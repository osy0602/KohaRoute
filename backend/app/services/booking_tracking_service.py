"""Privacy-limited donor booking tracking lookup (US-03)."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus

MISSED_BOOKING_MESSAGE = "The centre will contact you to reschedule this pickup."


class BookingNotFoundError(LookupError):
    """Raised when a reference does not match a booking."""


@dataclass(frozen=True)
class BookingTracking:
    """Only the fields a donor is allowed to see while tracking a booking."""

    status: str
    pickup_date: date
    address_area: str
    rejection_reason: str | None
    missed_message: str | None


def _partial_address(address: str) -> str:
    """Return suburb/area only, never the street address or house number."""
    ignored = {"au", "nz", "nzl", "new zealand"}
    parts = [part.strip() for part in address.split(",") if part.strip()]
    area_parts = [part for part in parts[1:] if part.casefold() not in ignored]
    return ", ".join(area_parts[-2:]) if area_parts else "Auckland region"


def track_booking(db: Session, reference: str) -> BookingTracking:
    """Find a booking by exact reference and return only public tracking fields."""
    normalized_reference = reference.strip()
    booking = db.scalar(select(Booking).where(Booking.reference == normalized_reference))
    if booking is None:
        raise BookingNotFoundError("No booking found")

    status_value = booking.status.value
    return BookingTracking(
        status=status_value,
        pickup_date=booking.pickup_date,
        address_area=_partial_address(booking.address_text),
        rejection_reason=(
            booking.rejection_reason if booking.status == BookingStatus.REJECTED else None
        ),
        missed_message=(MISSED_BOOKING_MESSAGE if booking.status == BookingStatus.MISSED else None),
    )
