"""Saved ORS route plans for one driver, vehicle, and pickup date (US-06)."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.route_stop import RouteStop
    from app.models.user import User
    from app.models.vehicle import Vehicle


class Route(TimestampMixin, Base):
    """A persisted optimization result; geometry and totals never require another ORS call."""

    __tablename__ = "routes"
    __table_args__ = (
        Index("ix_routes_pickup_date", "pickup_date"),
        Index("ix_routes_driver_pickup_date", "driver_id", "pickup_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pickup_date: Mapped[date] = mapped_column(Date, nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False)
    vehicle_name: Mapped[str] = mapped_column(String(80), nullable=False)
    vehicle_plate_number: Mapped[str] = mapped_column(String(6), nullable=False)
    vehicle_capacity_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_capacity_litres: Mapped[int] = mapped_column(Integer, nullable=False)
    total_distance_m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_weight_kg: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_volume_l: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geometry: Mapped[str] = mapped_column(Text, nullable=False, default="")
    color: Mapped[str] = mapped_column(String(7), nullable=False)

    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence",
        lazy="selectin",
    )
    driver: Mapped["User"] = relationship(foreign_keys=[driver_id])
    vehicle: Mapped["Vehicle"] = relationship(foreign_keys=[vehicle_id])