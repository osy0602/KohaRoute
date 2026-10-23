"""Column groups shared by several models."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.timeutil import utc_now_naive


class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` (both UTC) to a model."""

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive, nullable=False
    )
