"""Tests for donor booking dates, estimates and contact validation."""

from datetime import date

import pytest

from app.seed import seed_closed_dates, seed_settings
from app.services.booking_rules import (
    available_booking_dates,
    estimate_load,
    is_valid_nz_phone,
    validate_pickup_date,
)


@pytest.fixture()
def seeded(db_session):
    """Create the settings and holiday rows used by booking rules."""
    seed_settings(db_session)
    seed_closed_dates(db_session)
    return db_session


def test_available_dates_skip_weekends_and_holidays(seeded):
    """Only open weekdays through seven calendar days are offered."""
    window = available_booking_dates(seeded, date(2026, 10, 23))
    assert window.dates == (
        date(2026, 10, 27),
        date(2026, 10, 28),
        date(2026, 10, 29),
        date(2026, 10, 30),
    )
    assert window.earliest == date(2026, 10, 27)
    assert window.latest == date(2026, 10, 30)


def test_today_and_weekend_are_rejected_with_allowed_range(seeded):
    """The validation message states the allowed date range."""
    with pytest.raises(ValueError, match="2026-10-27 and 2026-10-30"):
        validate_pickup_date(seeded, date(2026, 10, 23), date(2026, 10, 23))
    with pytest.raises(ValueError, match="2026-10-27 and 2026-10-30"):
        validate_pickup_date(seeded, date(2026, 10, 24), date(2026, 10, 23))


def test_available_date_passes_validation(seeded):
    """An open date inside the booking window can be booked."""
    validate_pickup_date(seeded, date(2026, 10, 27), date(2026, 10, 23))


def test_estimate_uses_configured_preset_and_quantity(seeded):
    """Estimated totals use the stored size preset and quantity."""
    assert estimate_load(seeded, "medium", 3) == (45, 180)


@pytest.mark.parametrize("quantity", [0, 11])
def test_estimate_rejects_quantity_outside_settings(seeded, quantity):
    """Invalid quantities are rejected instead of producing a booking estimate."""
    with pytest.raises(ValueError, match="between 1 and 10"):
        estimate_load(seeded, "small", quantity)


def test_estimate_rejects_unknown_size(seeded):
    """Only seeded size presets can be used to calculate totals."""
    with pytest.raises(ValueError, match="valid item size"):
        estimate_load(seeded, "oversized", 1)


@pytest.mark.parametrize("phone", ["021 555 0101", "+64 21 555 0101", "09-123-4567"])
def test_valid_new_zealand_phone_formats(phone):
    """Common NZ mobile and landline formats are accepted."""
    assert is_valid_nz_phone(phone)


@pytest.mark.parametrize("phone", ["123456", "0800 ABC DEF", "+1 415 555 0100", "021 123"])
def test_invalid_phone_formats_are_rejected(phone):
    """Short, non-NZ, or non-numeric contacts are rejected."""
    assert not is_valid_nz_phone(phone)