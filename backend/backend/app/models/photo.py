"""Photos a donor uploads with a booking."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.timeutil import utc_now_naive

if TYPE_CHECKING:
    from app.models.booking import Booking


class Photo(Base):
    """Metadata of one stored photo. The image file itself lives on disk.

    The donor's original file name is never stored: ``stored_name`` is random, so a name can
    neither leak personal information nor be guessed.
    """

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stored_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, nullable=False)

    booking: Mapped["Booking"] = relationship(back_populates="photos")
