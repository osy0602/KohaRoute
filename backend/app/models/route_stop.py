"""Ordered booking stops saved as part of an ORS route plan (US-06)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.booking import BookingStatus
from app.models.types import string_enum
from app.timeutil import utc_now_naive

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.route import Route
    from app.models.user import User


class RouteStop(Base):
    """A booking at its ORS-ordered position on a route."""

    __tablename__ = "route_stops"
    __table_args__ = (
        UniqueConstraint("route_id", "sequence", name="uq_route_stops_route_sequence"),
        UniqueConstraint("route_id", "booking_id", name="uq_route_stops_route_booking"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        string_enum(BookingStatus, "route_stop_status"),
        nullable=False,
        default=BookingStatus.SCHEDULED,
    )
    remark: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)

    route: Mapped["Route"] = relationship(back_populates="stops")
    booking: Mapped["Booking"] = relationship()
    updated_by: Mapped["User | None"] = relationship(foreign_keys=[updated_by_user_id])