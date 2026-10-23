"""Open-day rules. Pure functions with no database access, so they are trivial to test.

The booking window (Part 3) is built on top of these.
"""

from collections.abc import Collection
from datetime import date, timedelta

# How far ahead to look before deciding there are no open days at all.
SEARCH_LIMIT_DAYS = 400


def is_open_day(day: date, opening_days: Collection[int], closed_dates: Collection[date]) -> bool:
    """Say whether the centre collects on a given date.

    Args:
        day: The date to check.
        opening_days: Weekdays the centre opens, Monday=0 to Sunday=6 (as ``date.weekday``).
        closed_dates: Public holidays and other dates the centre is closed.

    Returns:
        True if the weekday is an opening day and the date is not a closed date.
    """
    return day.weekday() in opening_days and day not in closed_dates


def next_open_days(
    after: date,
    count: int,
    opening_days: Collection[int],
    closed_dates: Collection[date],
) -> list[date]:
    """List the first open days strictly after a date.

    Args:
        after: Start point. This date itself is never included, so "today" is never offered.
        count: How many open days to return.
        opening_days: Weekdays the centre opens, Monday=0 to Sunday=6.
        closed_dates: Dates the centre is closed.

    Returns:
        The next ``count`` open days in date order.

    Raises:
        ValueError: If fewer than ``count`` open days exist within the search limit, which
            means the opening days setting is empty or wrong.
    """
    found: list[date] = []
    candidate = after
    for _ in range(SEARCH_LIMIT_DAYS):
        candidate += timedelta(days=1)
        if is_open_day(candidate, opening_days, closed_dates):
            found.append(candidate)
            if len(found) == count:
                return found
    raise ValueError("could not find enough open days; check the opening days setting")
