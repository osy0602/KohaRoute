"""New Zealand time helpers.

Every "today" in KohaRoute (booking window, opening days, closed dates) must be the date in
New Zealand, whatever time zone the server runs in. A server in UTC is still on yesterday's
date for up to 13 hours of the NZ day, so calling ``date.today()`` anywhere else in the code
would let donors book a same-day pickup by mistake. Always use ``today_nz`` instead.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

NZ_TIMEZONE = ZoneInfo("Pacific/Auckland")


def to_nz_time(moment: datetime) -> datetime:
    """Convert a time-zone-aware moment to New Zealand time.

    Args:
        moment: Any aware datetime (UTC, NZ, anything else).

    Returns:
        The same instant expressed in New Zealand time, daylight saving included.

    Raises:
        ValueError: If ``moment`` has no time zone. A naive time is ambiguous, so guessing
            its zone would hide bugs.
    """
    if moment.tzinfo is None:
        raise ValueError("moment must be timezone-aware")
    return moment.astimezone(NZ_TIMEZONE)


def today_nz(now: datetime | None = None) -> date:
    """Return today's calendar date in New Zealand.

    Args:
        now: Optional aware datetime to treat as "the current moment". Tests pass this so
            they do not depend on the real clock; production code leaves it out.

    Returns:
        The New Zealand calendar date for that moment.
    """
    moment = now if now is not None else datetime.now(UTC)
    return to_nz_time(moment).date()


def utc_now_naive() -> datetime:
    """Return the current UTC time without time-zone information.

    Database timestamps (``created_at`` and so on) are stored in UTC. SQLite cannot keep a
    time zone with a value, so we drop it here on purpose and convert to NZ time only when a
    time is shown to a person.

    Returns:
        The current moment in UTC as a naive datetime.
    """
    return datetime.now(UTC).replace(tzinfo=None)
