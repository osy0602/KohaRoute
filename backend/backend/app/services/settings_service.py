"""Read and write the business settings stored in the database.

All rules (opening days, booking window, size presets, depot, ...) are read through
``load_business_settings`` so the rest of the code never touches raw setting rows.
"""

from dataclasses import dataclass
from datetime import date, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClosedDate, Setting, SettingKey

BYTES_PER_MB = 1024 * 1024


class MissingSettingError(RuntimeError):
    """Raised when a required setting is not in the database."""


@dataclass(frozen=True)
class LoadEstimate:
    """Estimated weight and volume of a donation."""

    weight_kg: int
    volume_l: int


@dataclass(frozen=True)
class SizePreset:
    """One size choice on the booking form, such as "Medium"."""

    key: str
    label: str
    description: str
    weight_kg: int
    volume_l: int

    def estimate(self, quantity: int) -> LoadEstimate:
        """Scale the preset by a quantity.

        Args:
            quantity: Number of items of this size (at least 1).

        Returns:
            Estimated total weight in whole kg and volume in whole litres.

        Raises:
            ValueError: If the quantity is less than 1.
        """
        if quantity < 1:
            raise ValueError("quantity must be at least 1")
        return LoadEstimate(self.weight_kg * quantity, self.volume_l * quantity)


@dataclass(frozen=True)
class Depot:
    """Where every route starts and ends."""

    name: str
    address: str
    latitude: float
    longitude: float
    is_geocoded: bool


@dataclass(frozen=True)
class BusinessSettings:
    """All business rules, validated and typed. ``opening_days`` uses Monday=0 to Sunday=6."""

    opening_days: tuple[int, ...]
    opening_time: time
    closing_time: time
    booking_window_days: int
    max_quantity: int
    min_photos: int
    max_photos: int
    max_photo_bytes: int
    description_max_chars: int
    session_minutes: int
    size_presets: tuple[SizePreset, ...]
    depot: Depot

    def size_preset(self, key: str) -> SizePreset:
        """Find a size preset by its key.

        Args:
            key: Preset key such as "small", "medium" or "large".

        Returns:
            The matching preset.

        Raises:
            KeyError: If no preset has that key.
        """
        for preset in self.size_presets:
            if preset.key == key:
                return preset
        raise KeyError(f"unknown size: {key}")


def upsert_setting(db: Session, key: SettingKey, value: Any) -> None:
    """Create a setting or replace its value. The caller commits.

    Args:
        db: Open database session.
        key: Which setting to write.
        value: Any JSON-serialisable value.
    """
    setting = db.get(Setting, key.value)
    if setting is None:
        db.add(Setting(key=key.value, value=value))
    else:
        setting.value = value


def _require(values: dict[str, Any], key: SettingKey) -> Any:
    """Fetch one raw setting value or explain how to fix its absence."""
    try:
        return values[key.value]
    except KeyError:
        raise MissingSettingError(
            f"Setting '{key.value}' is missing. Run: python -m app.seed"
        ) from None


def load_business_settings(db: Session) -> BusinessSettings:
    """Load every business rule in a single query.

    The settings table has about a dozen rows, so reading it whole on demand is cheaper and
    simpler than caching it (and a cache could show stale rules after the seed script runs).

    Args:
        db: Open database session.

    Returns:
        The typed settings.

    Raises:
        MissingSettingError: If any setting has not been seeded.
    """
    values = {row.key: row.value for row in db.scalars(select(Setting))}

    def get(key: SettingKey) -> Any:
        return _require(values, key)

    return BusinessSettings(
        opening_days=tuple(get(SettingKey.OPENING_DAYS)),
        opening_time=time.fromisoformat(get(SettingKey.OPENING_TIME)),
        closing_time=time.fromisoformat(get(SettingKey.CLOSING_TIME)),
        booking_window_days=get(SettingKey.BOOKING_WINDOW_DAYS),
        max_quantity=get(SettingKey.MAX_QUANTITY),
        min_photos=get(SettingKey.MIN_PHOTOS),
        max_photos=get(SettingKey.MAX_PHOTOS),
        max_photo_bytes=get(SettingKey.MAX_PHOTO_MB) * BYTES_PER_MB,
        description_max_chars=get(SettingKey.DESCRIPTION_MAX_CHARS),
        session_minutes=get(SettingKey.SESSION_MINUTES),
        size_presets=tuple(SizePreset(**item) for item in get(SettingKey.SIZE_PRESETS)),
        depot=Depot(**get(SettingKey.DEPOT)),
    )


def load_closed_dates(db: Session) -> frozenset[date]:
    """Return every closed date as a set, for fast "is this date closed?" checks.

    Args:
        db: Open database session.

    Returns:
        The closed dates (public holidays) as an immutable set.
    """
    return frozenset(db.scalars(select(ClosedDate.closed_on)))
