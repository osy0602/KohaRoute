"""Donor pickup bookings and their category links."""

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin
from app.models.types import string_enum

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.photo import Photo


class BookingStatus(StrEnum):
    """The single status set used by every story."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    MISSED = "missed"


class BookingCategory(Base):
    """Link row: one category chosen on one booking (a booking can have several)."""

    __tablename__ = "booking_categories"

    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), primary_key=True
    )


class Booking(TimestampMixin, Base):
    """One donor's pickup request.

    Weight and volume are the *estimates* worked out from the size preset and quantity when
    the booking is made; drivers never enter a real weight. Weight is in whole kg and volume
    in whole litres.
    """

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_bookings_quantity_at_least_one"),
        CheckConstraint(
            "estimated_weight_kg >= 0 AND estimated_volume_l >= 0",
            name="ck_bookings_estimates_not_negative",
        ),
        # Admin list: "Pending bookings" or "Approved bookings for this date".
        Index("ix_bookings_status_pickup_date", "status", "pickup_date"),
        # Map and route planning: "everything for this date".
        Index("ix_bookings_pickup_date", "pickup_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Random and unguessable (generated in Part 3). The unique rule also creates the index
    # that makes tracking by reference fast.
    reference: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    donor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_number: Mapped[str] = mapped_column(String(32), nullable=False)
    address_text: Mapped[str] = mapped_column(String(255), nullable=False)
    # Saved once from the ORS suggestion so the address is never looked up again.
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_date: Mapped[date] = mapped_column(Date, nullable=False)
    size: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    estimated_weight_kg: Mapped[int] = mapped_column(nullable=False)
    estimated_volume_l: Mapped[int] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[BookingStatus] = mapped_column(
        string_enum(BookingStatus, "booking_status"),
        default=BookingStatus.PENDING,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # lazy="selectin" loads the categories and photos of a whole list of bookings in one extra
    # query each, instead of one query per booking (the "N+1" problem).
    categories: Mapped[list["Category"]] = relationship(
        secondary="booking_categories",
        order_by="Category.sort_order",
        lazy="selectin",
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="Photo.id",
        lazy="selectin",
    )
