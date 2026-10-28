from datetime import date

import pytest

from app.services.calendar_service import is_open_day, next_open_days

WEEKDAYS = (0, 1, 2, 3, 4)
LABOUR_DAY_2026 = date(2026, 10, 26)  # a Monday public holiday


def test_weekday_is_open():
    assert is_open_day(date(2026, 10, 16), WEEKDAYS, set())  # Friday


@pytest.mark.parametrize("weekend_day", [date(2026, 10, 17), date(2026, 10, 18)])
def test_weekend_is_closed(weekend_day):
    assert not is_open_day(weekend_day, WEEKDAYS, set())


def test_public_holiday_is_closed_even_on_a_weekday():
    assert not is_open_day(LABOUR_DAY_2026, WEEKDAYS, {LABOUR_DAY_2026})


def test_next_open_days_never_includes_the_start_date():
    assert next_open_days(date(2026, 10, 15), 2, WEEKDAYS, set()) == [
        date(2026, 10, 16),
        date(2026, 10, 19),
    ]


def test_next_open_days_skips_weekend_and_holiday():
    result = next_open_days(date(2026, 10, 23), 3, WEEKDAYS, {LABOUR_DAY_2026})
    assert result == [date(2026, 10, 27), date(2026, 10, 28), date(2026, 10, 29)]


def test_next_open_days_fails_clearly_when_nothing_is_ever_open():
    with pytest.raises(ValueError, match="opening days"):
        next_open_days(date(2026, 10, 15), 1, (), set())
