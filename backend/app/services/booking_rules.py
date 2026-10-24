"""Booking-specific validation and estimation rules (US-02)."""

import re
from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.services.calendar_service import is_open_day
from app.services.settings_service import load_business_settings, load_closed_dates
from app.timeutil import today_nz

_NZ_PHONE_DIGITS = re.compile(r"^(?:0[2-9]\d{7,9}|64[2-9]\d{7,9})$")


class BookingDateWindow(NamedTuple):
    """Earliest and latest valid dates, plus all open dates in between."""

    earliest: date
    latest: date
    dates: tuple[date, ...]


def available_booking_dates(db: Session, today: date | None = None) -> BookingDateWindow:
    """Return open dates after NZ-local today through the configured calendar window."""
    settings = load_business_settings(db)
    closed_dates = load_closed_dates(db)
    current_day = today or today_nz()
    dates = tuple(
        day
        for offset in range(1, settings.booking_window_days + 1)
        if is_open_day(
            day := current_day + timedelta(days=offset), settings.opening_days, closed_dates
        )
    )
    if not dates:
        raise ValueError("There are no available pickup dates in the booking window.")
    return BookingDateWindow(dates[0], dates[-1], dates)


def validate_pickup_date(db: Session, pickup_date: date, today: date | None = None) -> None:
    """Reject a date unless it is an open day in the current booking window."""
    window = available_booking_dates(db, today)
    if pickup_date not in window.dates:
        raise ValueError(
            "Choose an open pickup date between "
            f"{window.earliest.isoformat()} and {window.latest.isoformat()}."
        )


def estimate_load(db: Session, size_key: str, quantity: int) -> tuple[int, int]:
    """Return estimated whole-kilogram and litre totals from configured presets."""
    settings = load_business_settings(db)
    if quantity < 1 or quantity > settings.max_quantity:
        raise ValueError(f"Quantity must be between 1 and {settings.max_quantity}.")
    try:
        estimate = settings.size_preset(size_key).estimate(quantity)
    except KeyError:
        raise ValueError("Choose a valid item size.") from None
    return estimate.weight_kg, estimate.volume_l


def is_valid_nz_phone(value: str) -> bool:
    """Validate common New Zealand national or +64 phone number formats."""
    digits = re.sub(r"[\s().-]", "", value)
    if digits.startswith("+"):
        digits = digits[1:]
    return bool(_NZ_PHONE_DIGITS.fullmatch(digits))