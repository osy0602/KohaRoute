"""Session length rule (US-01 technical note: "Session length comes from settings").

The value lives in the ``settings`` table (``session_minutes``, seeded as 480). This is
the only place Part 2 reads that table, so a different column layout changes one file.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Setting

SESSION_MINUTES_KEY = "session_minutes"
DEFAULT_SESSION_MINUTES = 480  # 8 hours, used only if the row is missing or invalid


def get_session_minutes(db: Session) -> int:
    """Return how long a login lasts, in minutes."""
    raw_value = db.scalars(select(Setting.value).where(Setting.key == SESSION_MINUTES_KEY)).first()
    try:
        minutes = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_SESSION_MINUTES
    return minutes if minutes > 0 else DEFAULT_SESSION_MINUTES
