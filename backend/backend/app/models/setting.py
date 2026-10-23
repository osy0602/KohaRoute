"""Business settings stored as key/value rows."""

from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TimestampMixin


class SettingKey(StrEnum):
    """Every setting name, defined once so the seed script and the reader cannot drift apart."""

    OPENING_DAYS = "opening_days"
    OPENING_TIME = "opening_time"
    CLOSING_TIME = "closing_time"
    BOOKING_WINDOW_DAYS = "booking_window_days"
    MAX_QUANTITY = "max_quantity"
    MIN_PHOTOS = "min_photos"
    MAX_PHOTOS = "max_photos"
    MAX_PHOTO_MB = "max_photo_mb"
    DESCRIPTION_MAX_CHARS = "description_max_chars"
    SESSION_MINUTES = "session_minutes"
    SIZE_PRESETS = "size_presets"
    DEPOT = "depot"


class Setting(TimestampMixin, Base):
    """One business rule, such as the booking window or the depot location."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
