"""Admin booking review queries and state transitions (US-04)."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Booking, BookingStatus
from app.services.booking_rules import validate_pickup_date


class BookingNotFoundError(LookupError):
    """Raised when an Admin requests a booking that does not exist."""


class InvalidBookingTransitionError(RuntimeError):
    """Raised when an action is not allowed from a booking's current status."""


def get_booking_for_admin(db: Session, booking_id: int) -> Booking:
    """Fetch a booking with its categories and photos loaded for Admin display."""
    statement = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(selectinload(Booking.categories), selectinload(Booking.photos))
    )
    booking = db.scalar(statement)
    if booking is None:
        raise BookingNotFoundError("Booking not found")
    return booking


def list_bookings_for_admin(
    db: Session, status_filter: BookingStatus | None, pickup_date: date | None
) -> list[Booking]:
    """Return a filtered, ordered Admin list with category and photo data batch-loaded."""
    statement = select(Booking).options(
        selectinload(Booking.categories), selectinload(Booking.photos)
    )
    if status_filter is not None:
        statement = statement.where(Booking.status == status_filter)
    if pickup_date is not None:
        statement = statement.where(Booking.pickup_date == pickup_date)
    statement = statement.order_by(Booking.pickup_date, Booking.created_at.desc(), Booking.id)
    return list(db.scalars(statement).all())


def approve_booking(db: Session, booking_id: int) -> Booking:
    """Move a Pending booking to Approved."""
    booking = get_booking_for_admin(db, booking_id)
    if booking.status != BookingStatus.PENDING:
        raise InvalidBookingTransitionError("Only Pending bookings can be approved.")
    booking.status = BookingStatus.APPROVED
    db.commit()
    return get_booking_for_admin(db, booking_id)


def reject_booking(db: Session, booking_id: int, reason: str) -> Booking:
    """Move a Pending booking to Rejected and save the required reason."""
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ValueError("Enter a reason for rejecting this booking.")
    booking = get_booking_for_admin(db, booking_id)
    if booking.status != BookingStatus.PENDING:
        raise InvalidBookingTransitionError("Only Pending bookings can be rejected.")
    booking.status = BookingStatus.REJECTED
    booking.rejection_reason = normalized_reason
    db.commit()
    return get_booking_for_admin(db, booking_id)


def reschedule_booking(db: Session, booking_id: int, pickup_date: date) -> Booking:
    """Reschedule an Approved or Missed booking onto an open date and keep it Approved."""
    booking = get_booking_for_admin(db, booking_id)
    if booking.status not in {BookingStatus.APPROVED, BookingStatus.MISSED}:
        raise InvalidBookingTransitionError("Only Approved or Missed bookings can be rescheduled.")
    validate_pickup_date(db, pickup_date)
    booking.pickup_date = pickup_date
    booking.status = BookingStatus.APPROVED
    db.commit()
    return get_booking_for_admin(db, booking_id)
