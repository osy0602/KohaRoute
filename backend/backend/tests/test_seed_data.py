from collections import Counter
from datetime import date

from app.models import BookingStatus, SettingKey
from app.seed_data import CATEGORY_NAMES, DEFAULT_SETTINGS, DEMO_BOOKINGS, NZ_CLOSED_DATES

HOLIDAY_DATES = [day for day, _name in NZ_CLOSED_DATES]


def test_closed_dates_are_unique():
    assert len(HOLIDAY_DATES) == len(set(HOLIDAY_DATES))


def test_closed_dates_cover_2026_and_2027_with_twelve_weekdays_each():
    assert Counter(day.year for day in HOLIDAY_DATES) == {2026: 12, 2027: 12}


def test_every_closed_date_is_a_weekday():
    # Weekend holidays are listed on the Monday or Tuesday they are observed.
    assert all(day.weekday() < 5 for day in HOLIDAY_DATES)


def test_auckland_anniversary_day_is_included_for_both_years():
    names = dict(NZ_CLOSED_DATES)
    assert names[date(2026, 1, 26)] == "Auckland Anniversary Day"
    assert names[date(2027, 2, 1)] == "Auckland Anniversary Day"


def test_weekend_holidays_are_listed_on_their_observed_day():
    assert date(2027, 12, 27) in HOLIDAY_DATES and date(2027, 12, 25) not in HOLIDAY_DATES
    assert date(2027, 12, 28) in HOLIDAY_DATES and date(2027, 12, 26) not in HOLIDAY_DATES
    assert date(2026, 12, 28) in HOLIDAY_DATES and date(2026, 12, 26) not in HOLIDAY_DATES
    assert date(2027, 1, 4) in HOLIDAY_DATES and date(2027, 1, 2) not in HOLIDAY_DATES


def test_every_setting_key_has_a_default():
    assert set(DEFAULT_SETTINGS) == set(SettingKey)


def test_category_names_are_unique():
    assert len(CATEGORY_NAMES) == len(set(CATEGORY_NAMES)) == 6


def test_demo_bookings_are_consistent():
    size_keys = {preset["key"] for preset in DEFAULT_SETTINGS[SettingKey.SIZE_PRESETS]}
    references = [booking.reference for booking in DEMO_BOOKINGS]
    assert len(references) == len(set(references))
    for booking in DEMO_BOOKINGS:
        assert booking.size in size_keys
        assert 1 <= booking.quantity <= 10
        assert set(booking.category_names) <= set(CATEGORY_NAMES)
        assert booking.status in {
            BookingStatus.PENDING,
            BookingStatus.APPROVED,
            BookingStatus.REJECTED,
        }
        assert (booking.status is BookingStatus.REJECTED) == bool(booking.rejection_reason)
