"""Dates on which the centre does not collect (public holidays)."""

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClosedDate(Base):
    """A weekday the centre is closed. Weekends are handled by the opening days setting."""

    __tablename__ = "closed_dates"

    # The date itself is the primary key: it is unique, and lookups by date are instant.
    closed_on: Mapped[date] = mapped_column(Date, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
