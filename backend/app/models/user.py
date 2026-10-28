"""Staff accounts (Admin and drivers). Donors have no accounts."""

from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.database import Base
from app.models.mixins import TimestampMixin
from app.models.types import string_enum


class UserRole(StrEnum):
    """What a staff member is allowed to do."""

    ADMIN = "admin"
    DRIVER = "driver"


class User(TimestampMixin, Base):
    """A staff member who can log in."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[UserRole] = mapped_column(string_enum(UserRole, "user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    @validates("email")
    def _normalise_email(self, _key: str, value: str) -> str:
        """Store emails in lower case so login is not case sensitive."""
        return value.strip().lower()
