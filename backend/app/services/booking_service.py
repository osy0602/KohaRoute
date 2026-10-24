"""Transactional donor booking creation and persistent photo storage (US-02)."""

import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, Category, Photo
from app.services.booking_rules import estimate_load, is_valid_nz_phone, validate_pickup_date
from app.services.geocoding_service import (
    AddressSelection,
    InvalidAddressSelectionError,
    verify_address_selection,
)
from app.services.photo_service import PreparedPhoto
from app.services.settings_service import load_business_settings

REFERENCE_LENGTH = 15
REFERENCE_ATTEMPTS = 5


class BookingValidationError(ValueError):
    """A field-level error that the booking API can return without saving data."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


@dataclass(frozen=True)
class BookingDetails:
    """Validated donor-provided booking fields and the selected category IDs."""

    donor_name: str
    contact_number: str
    address_token: str
    pickup_date: date
    size: str
    quantity: int
    category_ids: tuple[int, ...]
    description: str | None


def _new_reference(db: Session) -> str:
    """Generate a random, non-sequential reference that is unique in the database."""
    for _ in range(REFERENCE_ATTEMPTS):
        reference = secrets.token_urlsafe(REFERENCE_LENGTH)[:24]
        exists = db.scalar(select(Booking.id).where(Booking.reference == reference))
        if exists is None:
            return reference
    raise RuntimeError("Could not generate a unique booking reference.")


def _validate_details(db: Session, details: BookingDetails) -> tuple[AddressSelection, int, int]:
    """Validate field-level business rules before creating any database or file state."""
    donor_name = details.donor_name.strip()
    if not donor_name or len(donor_name) > 120:
        raise BookingValidationError("donor_name", "Enter a name up to 120 characters.")
    contact_number = details.contact_number.strip()
    if not is_valid_nz_phone(contact_number):
        raise BookingValidationError("contact_number", "Enter a valid New Zealand phone number.")
    if not details.category_ids:
        raise BookingValidationError("category_ids", "Choose at least one item category.")

    settings = load_business_settings(db)
    description = details.description.strip() if details.description else ""
    if len(description) > settings.description_max_chars:
        raise BookingValidationError(
            "description",
            f"Description must be no more than {settings.description_max_chars} characters.",
        )

    try:
        validate_pickup_date(db, details.pickup_date)
    except ValueError as error:
        raise BookingValidationError("pickup_date", str(error)) from error
    try:
        weight_kg, volume_l = estimate_load(db, details.size, details.quantity)
    except ValueError as error:
        field = "quantity" if "quantity" in str(error).lower() else "size"
        raise BookingValidationError(field, str(error)) from error
    try:
        address = verify_address_selection(details.address_token)
    except InvalidAddressSelectionError as error:
        raise BookingValidationError("address", str(error)) from error

    unique_ids = set(details.category_ids)
    categories = db.scalars(
        select(Category).where(Category.id.in_(unique_ids), Category.is_active.is_(True))
    ).all()
    if len(categories) != len(unique_ids):
        raise BookingValidationError("category_ids", "Choose valid item categories.")
    return address, weight_kg, volume_l


def create_booking(
    db: Session,
    details: BookingDetails,
    photos: tuple[PreparedPhoto, ...],
    photo_directory: Path,
) -> Booking:
    """Validate and save a Pending booking and its photo bytes as one recoverable operation."""
    address, weight_kg, volume_l = _validate_details(db, details)
    settings = load_business_settings(db)
    if not settings.min_photos <= len(photos) <= settings.max_photos:
        raise BookingValidationError(
            "photos",
            f"Upload between {settings.min_photos} and {settings.max_photos} photos.",
        )
    if any(len(photo.content) > settings.max_photo_bytes for photo in photos):
        raise BookingValidationError("photos", "Each photo must be no larger than 5 MB.")

    category_ids = set(details.category_ids)
    categories = db.scalars(select(Category).where(Category.id.in_(category_ids))).all()
    booking = Booking(
        reference=_new_reference(db),
        donor_name=details.donor_name.strip(),
        contact_number=details.contact_number.strip(),
        address_text=address.label,
        latitude=address.latitude,
        longitude=address.longitude,
        pickup_date=details.pickup_date,
        size=details.size,
        quantity=details.quantity,
        estimated_weight_kg=weight_kg,
        estimated_volume_l=volume_l,
        description=(details.description.strip() or None) if details.description else None,
        status=BookingStatus.PENDING,
        categories=categories,
    )
    stored_paths: list[Path] = []
    try:
        photo_directory.mkdir(parents=True, exist_ok=True)
        db.add(booking)
        db.flush()
        for prepared in photos:
            stored_name = f"{secrets.token_hex(24)}.{prepared.extension}"
            path = photo_directory / stored_name
            with path.open("xb") as image_file:
                stored_paths.append(path)
                image_file.write(prepared.content)
            db.add(
                Photo(
                    booking_id=booking.id,
                    stored_name=stored_name,
                    content_type=prepared.content_type,
                    size_bytes=len(prepared.content),
                )
            )
        db.commit()
        return booking
    except Exception:
        db.rollback()
        for path in stored_paths:
            path.unlink(missing_ok=True)
        raise