"""Vehicles the centre can send out."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.database import Base
from app.models.mixins import TimestampMixin


class Vehicle(TimestampMixin, Base):
    """A vehicle with a weight and volume capacity.

    Capacity is stored in whole kilograms and whole litres because the ORS Optimization API
    accepts whole numbers only. (0.8 m3 is stored as 800 litres.)
    """

    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("capacity_kg > 0", name="ck_vehicles_capacity_kg_positive"),
        CheckConstraint("capacity_litres > 0", name="ck_vehicles_capacity_litres_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(6), unique=True, nullable=False)
    capacity_kg: Mapped[int] = mapped_column(nullable=False)
    capacity_litres: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    @validates("plate_number")
    def _normalise_plate(self, _key: str, value: str) -> str:
        """Store plates in upper case so "abc123" and "ABC123" count as the same plate."""
        return value.strip().upper()
