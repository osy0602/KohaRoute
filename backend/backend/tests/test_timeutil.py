from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.timeutil import to_nz_time, today_nz, utc_now_naive

# NZ daylight time (UTC+13) runs from 27 Sep 2026; standard time (UTC+12) applies in July.


@pytest.mark.parametrize(
    ("utc_moment", "expected_nz_date"),
    [
        (datetime(2026, 10, 14, 10, 59, tzinfo=UTC), date(2026, 10, 14)),  # 23:59 NZDT
        (datetime(2026, 10, 14, 11, 0, tzinfo=UTC), date(2026, 10, 15)),  # 00:00 NZDT
        (datetime(2026, 7, 1, 11, 59, tzinfo=UTC), date(2026, 7, 1)),  # 23:59 NZST
        (datetime(2026, 7, 1, 12, 0, tzinfo=UTC), date(2026, 7, 2)),  # 00:00 NZST
    ],
)
def test_today_nz_flips_at_new_zealand_midnight(utc_moment, expected_nz_date):
    assert today_nz(utc_moment) == expected_nz_date


def test_today_nz_handles_daylight_saving_start():
    before = datetime(2026, 9, 26, 11, 59, tzinfo=UTC)  # 23:59 NZST on 26 Sep
    after = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)  # 00:00 NZST on 27 Sep
    assert today_nz(before) == date(2026, 9, 26)
    assert today_nz(after) == date(2026, 9, 27)


def test_today_nz_accepts_any_time_zone():
    los_angeles_evening = datetime(2026, 10, 14, 17, 0, tzinfo=timezone(timedelta(hours=-7)))
    assert today_nz(los_angeles_evening) == date(2026, 10, 15)  # 13:00 NZDT next day


def test_to_nz_time_rejects_naive_datetime():
    with pytest.raises(ValueError, match="timezone-aware"):
        to_nz_time(datetime(2026, 10, 15, 9, 0))


def test_today_nz_without_argument_returns_a_date():
    assert isinstance(today_nz(), date)


def test_utc_now_naive_has_no_time_zone():
    assert utc_now_naive().tzinfo is None
