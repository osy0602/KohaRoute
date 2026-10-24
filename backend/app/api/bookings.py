"""Public donor booking options, address suggestions and booking creation (US-02)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_config
from app.database import get_db
from app.models import Category
from app.schemas.bookings import (
    AddressSuggestionResponse,
    BookingCreatedResponse,
    BookingOptionsResponse,
    CategoryOption,
    SizePresetOption,
)
from app.services.booking_rules import available_booking_dates
from app.services.booking_service import BookingDetails, BookingValidationError, create_booking
from app.services.geocoding_service import (
    AddressRateLimiter,
    AddressSearchService,
    GeocoderUnavailableError,
)
from app.services.photo_service import InvalidPhotoError, prepare_photo
from app.services.settings_service import load_business_settings

router = APIRouter(prefix="/api/bookings", tags=["bookings"])
MAX_REFERENCE_ATTEMPTS = 5


def get_address_search(request: Request) -> AddressSearchService:
    """Return the application's shared, cached address search service."""
    return request.app.state.address_search


def get_address_rate_limiter(request: Request) -> AddressRateLimiter:
    """Return the application's per-process address request limiter."""
    return request.app.state.address_rate_limiter


@router.get("/options", response_model=BookingOptionsResponse)
def read_booking_options(db: Annotated[Session, Depends(get_db)]) -> BookingOptionsResponse:
    """Return active categories, size presets and server-derived booking limits."""
    settings = load_business_settings(db)
    window = available_booking_dates(db)
    categories = db.scalars(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.id)
    ).all()
    presets = [SizePresetOption(**preset.__dict__) for preset in settings.size_presets]
    return BookingOptionsResponse(
        pickup_dates=list(window.dates),
        earliest_pickup_date=window.earliest,
        latest_pickup_date=window.latest,
        categories=[CategoryOption.model_validate(category) for category in categories],
        size_presets=presets,
        max_quantity=settings.max_quantity,
        min_photos=settings.min_photos,
        max_photos=settings.max_photos,
        max_photo_size_bytes=settings.max_photo_bytes,
        description_max_chars=settings.description_max_chars,
    )


@router.get("/address-suggestions", response_model=list[AddressSuggestionResponse])
async def read_address_suggestions(
    request: Request,
    query: Annotated[str, Query(min_length=3, max_length=160)],
    search: Annotated[AddressSearchService, Depends(get_address_search)],
    limiter: Annotated[AddressRateLimiter, Depends(get_address_rate_limiter)],
) -> list[AddressSuggestionResponse]:
    """Search ORS for Auckland addresses and return expiring signed selections."""
    client_key = request.client.host if request.client else "unknown"
    if not limiter.allow(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many address searches. Please wait and try again.",
            headers={"Retry-After": "60"},
        )
    try:
        suggestions = await search.suggestions(query)
    except GeocoderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    return [AddressSuggestionResponse(label=item.label, token=item.token) for item in suggestions]


@router.post("", response_model=BookingCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_donor_booking(
    donor_name: Annotated[str, Form(min_length=1, max_length=120)],
    contact_number: Annotated[str, Form(min_length=1, max_length=32)],
    address_token: Annotated[str, Form(min_length=1)],
    pickup_date: Annotated[date, Form()],
    size: Annotated[str, Form(min_length=1, max_length=16)],
    quantity: Annotated[int, Form(ge=1)],
    category_ids: Annotated[list[int], Form()],
    db: Annotated[Session, Depends(get_db)],
    description: Annotated[str | None, Form(max_length=300)] = None,
    photos: Annotated[list[UploadFile] | None, File()] = None,
) -> BookingCreatedResponse:
    """Validate a multipart donor submission and create its Pending booking."""
    settings = load_business_settings(db)
    photo_files = photos or []
    if not settings.min_photos <= len(photo_files) <= settings.max_photos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "field": "photos",
                "message": (
                    f"Upload between {settings.min_photos} and {settings.max_photos} photos."
                ),
            },
        )

    prepared_photos = []
    for photo in photo_files:
        try:
            content = await photo.read(settings.max_photo_bytes + 1)
            prepared_photos.append(prepare_photo(content, settings.max_photo_bytes))
        except InvalidPhotoError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"field": "photos", "message": str(error)},
            ) from error
        finally:
            await photo.close()

    details = BookingDetails(
        donor_name=donor_name,
        contact_number=contact_number,
        address_token=address_token,
        pickup_date=pickup_date,
        size=size,
        quantity=quantity,
        category_ids=tuple(category_ids),
        description=description,
    )
    try:
        booking = create_booking(
            db,
            details,
            tuple(prepared_photos),
            Path(get_config().photo_storage_dir),
        )
    except BookingValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"field": error.field, "message": str(error)},
        ) from error
    except (OSError, RuntimeError, SQLAlchemyError) as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The booking could not be saved. Please try again.",
        ) from error

    return BookingCreatedResponse(
        reference=booking.reference,
        status=booking.status.value,
        pickup_date=booking.pickup_date,
        estimated_weight_kg=booking.estimated_weight_kg,
        estimated_volume_l=booking.estimated_volume_l,
    )