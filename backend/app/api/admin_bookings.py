"""Admin-only booking review and status transitions (US-04)."""

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.config import get_config
from app.database import get_db
from app.models import BookingStatus, Photo, RouteStop
from app.schemas.admin_bookings import (
    AdminBookingDetail,
    AdminBookingSummary,
    RejectBookingRequest,
    RescheduleBookingRequest,
)
from app.services.admin_booking_service import (
    BookingNotFoundError,
    InvalidBookingTransitionError,
    approve_booking,
    get_booking_for_admin,
    list_bookings_for_admin,
    reject_booking,
    reschedule_booking,
)

router = APIRouter(
    prefix="/api/admin/bookings",
    tags=["admin-bookings"],
    dependencies=[Depends(require_admin)],
)


def _latest_driver_remark(db: Session, booking_id: int) -> str | None:
    """Return the most recent driver remark for a booking, if one exists."""
    statement = (
        select(RouteStop.remark)
        .where(RouteStop.booking_id == booking_id, RouteStop.remark.is_not(None))
        .order_by(RouteStop.completed_at.desc(), RouteStop.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def _summary(booking, driver_remark: str | None = None) -> AdminBookingSummary:
    """Map a booking ORM row to the Admin list response."""
    return AdminBookingSummary(
        id=booking.id,
        reference=booking.reference,
        donor_name=booking.donor_name,
        address_text=booking.address_text,
        pickup_date=booking.pickup_date,
        category_names=[category.name for category in booking.categories],
        estimated_weight_kg=booking.estimated_weight_kg,
        estimated_volume_l=booking.estimated_volume_l,
        status=booking.status.value,
        driver_remark=driver_remark,
        photos=[{"id": photo.id, "content_type": photo.content_type} for photo in booking.photos],
        latitude=booking.latitude,
        longitude=booking.longitude,
    )


def _detail(booking, driver_remark: str | None = None) -> AdminBookingDetail:
    """Map all authorized booking details to the Admin response."""
    summary = _summary(booking, driver_remark)
    return AdminBookingDetail(
        **summary.model_dump(exclude={"latitude", "longitude"}),
        contact_number=booking.contact_number,
        size=booking.size,
        quantity=booking.quantity,
        latitude=booking.latitude,
        longitude=booking.longitude,
        description=booking.description,
        rejection_reason=booking.rejection_reason,
    )


def _get_booking(booking_id: int, db: Session):
    """Translate a missing booking into an HTTP not-found response."""
    try:
        return get_booking_for_admin(db, booking_id)
    except BookingNotFoundError as error:
        raise HTTPException(status_code=404, detail="Booking not found") from error


def _transition(action, *args):
    """Translate invalid state transitions and invalid reschedule dates to HTTP errors."""
    try:
        return action(*args)
    except BookingNotFoundError as error:
        raise HTTPException(status_code=404, detail="Booking not found") from error
    except InvalidBookingTransitionError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[AdminBookingSummary])
def read_admin_bookings(
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[str, Query(alias="status")] = "pending",
    pickup_date: date | None = None,
) -> list[AdminBookingSummary]:
    """List bookings, defaulting to Pending, with optional status and pickup-date filters."""
    if status_filter == "all":
        selected_status = None
    else:
        try:
            selected_status = BookingStatus(status_filter)
        except ValueError as error:
            allowed = ", ".join(["all", *(item.value for item in BookingStatus)])
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Status must be one of: {allowed}.",
            ) from error
    bookings = list_bookings_for_admin(db, selected_status, pickup_date)
    if not bookings:
        return []
    booking_ids = [booking.id for booking in bookings]
    stops = db.scalars(
        select(RouteStop)
        .where(RouteStop.booking_id.in_(booking_ids), RouteStop.remark.is_not(None))
        .order_by(RouteStop.completed_at.desc(), RouteStop.id.desc())
    ).all()
    remarks: dict[int, str] = {}
    for stop in stops:
        remarks.setdefault(stop.booking_id, stop.remark)
    return [_summary(booking, remarks.get(booking.id)) for booking in bookings]


@router.get("/{booking_id}", response_model=AdminBookingDetail)
def read_admin_booking(
    booking_id: int, db: Annotated[Session, Depends(get_db)]
) -> AdminBookingDetail:
    """Return full donor, description, photo, estimate, and map-coordinate details."""
    return _detail(_get_booking(booking_id, db), _latest_driver_remark(db, booking_id))


@router.get("/{booking_id}/photos/{photo_id}")
def read_admin_photo(
    booking_id: int,
    photo_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """Serve a private booking image only to an authenticated Admin."""
    booking = _get_booking(booking_id, db)
    photo = db.get(Photo, photo_id)
    if photo is None or photo.booking_id != booking.id:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo_directory = Path(get_config().photo_storage_dir).resolve()
    photo_path = (photo_directory / photo.stored_name).resolve()
    if photo_path.parent != photo_directory or not photo_path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(photo_path, media_type=photo.content_type)


@router.post("/{booking_id}/approve", response_model=AdminBookingDetail)
def approve_admin_booking(
    booking_id: int, db: Annotated[Session, Depends(get_db)]
) -> AdminBookingDetail:
    """Approve a Pending booking for later route planning."""
    return _detail(_transition(approve_booking, db, booking_id), _latest_driver_remark(db, booking_id))


@router.post("/{booking_id}/reject", response_model=AdminBookingDetail)
def reject_admin_booking(
    booking_id: int,
    payload: RejectBookingRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdminBookingDetail:
    """Reject a Pending booking and save the reason visible to the donor."""
    return _detail(
        _transition(reject_booking, db, booking_id, payload.reason),
        _latest_driver_remark(db, booking_id),
    )


@router.post("/{booking_id}/reschedule", response_model=AdminBookingDetail)
def reschedule_admin_booking(
    booking_id: int,
    payload: RescheduleBookingRequest,
    db: Annotated[Session, Depends(get_db)],
) -> AdminBookingDetail:
    """Reschedule an Approved or Missed booking to an open date."""
    return _detail(
        _transition(reschedule_booking, db, booking_id, payload.pickup_date),
        _latest_driver_remark(db, booking_id),
    )
