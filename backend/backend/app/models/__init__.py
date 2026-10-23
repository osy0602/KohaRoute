"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.models.booking import Booking, BookingCategory, BookingStatus
from app.models.category import Category
from app.models.closed_date import ClosedDate
from app.models.photo import Photo
from app.models.setting import Setting, SettingKey
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle

__all__ = [
    "Booking",
    "BookingCategory",
    "BookingStatus",
    "Category",
    "ClosedDate",
    "Photo",
    "Setting",
    "SettingKey",
    "User",
    "UserRole",
    "Vehicle",
]
