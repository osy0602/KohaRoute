"""Fixed data for the seed script: settings, holidays, categories and demo records.

This module is data only. The logic that writes it lives in ``app.seed``, so the client team
can review and correct these values without reading any code.

Everything marked "demo" (names, phone numbers, addresses, references) is fictional.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.models import BookingStatus, SettingKey

# --------------------------------------------------------------------------------------
# Settings (the business rules). To change one, edit it here and run `python -m app.seed`.
# --------------------------------------------------------------------------------------
DEFAULT_SETTINGS: dict[SettingKey, Any] = {
    SettingKey.OPENING_DAYS: [0, 1, 2, 3, 4],  # Monday=0 ... Friday=4
    SettingKey.OPENING_TIME: "09:00",
    SettingKey.CLOSING_TIME: "17:00",
    SettingKey.BOOKING_WINDOW_DAYS: 7,
    SettingKey.MAX_QUANTITY: 10,
    SettingKey.MIN_PHOTOS: 1,
    SettingKey.MAX_PHOTOS: 3,
    SettingKey.MAX_PHOTO_MB: 5,
    SettingKey.DESCRIPTION_MAX_CHARS: 300,
    SettingKey.SESSION_MINUTES: 480,
    # Awaiting client confirmation. Estimate = preset x quantity.
    SettingKey.SIZE_PRESETS: [
        {
            "key": "small",
            "label": "Small",
            "description": "A shopping bag or small box",
            "weight_kg": 5,
            "volume_l": 20,
        },
        {
            "key": "medium",
            "label": "Medium",
            "description": "A standard moving box or a large bag",
            "weight_kg": 15,
            "volume_l": 60,
        },
        {
            "key": "large",
            "label": "Large",
            "description": "A big box, several bags, or a small appliance",
            "weight_kg": 30,
            "volume_l": 150,
        },
    ],
    # Coordinates are approximate for Westgate. Part 3 replaces them with one ORS lookup and
    # sets is_geocoded to true.
    SettingKey.DEPOT: {
        "name": "Auckland Community Centre depot",
        "address": "11 Kohuhu Lane, Westgate, Auckland",
        "latitude": -36.8150,
        "longitude": 174.6100,
        "is_geocoded": False,
    },
}

# --------------------------------------------------------------------------------------
# Closed dates: NZ public holidays that fall on a weekday, 2026 and 2027, listed on the day
# they are *observed*. A holiday on a weekend is listed on the Monday or Tuesday it moves to,
# because the centre is closed on weekends anyway. Auckland Anniversary Day is included.
#
# Source: https://www.employment.govt.nz/leave-and-holidays/public-holidays/
#         public-holidays-and-anniversary-dates
# Checked 15 Oct 2026 (page last modified 25 Sep 2026). The source warns that regional
# anniversary dates may contain unintentional errors, so confirm before release.
# --------------------------------------------------------------------------------------
NZ_CLOSED_DATES: tuple[tuple[date, str], ...] = (
    # 2026
    (date(2026, 1, 1), "New Year's Day"),
    (date(2026, 1, 2), "Day after New Year's Day"),
    (date(2026, 1, 26), "Auckland Anniversary Day"),
    (date(2026, 2, 6), "Waitangi Day"),
    (date(2026, 4, 3), "Good Friday"),
    (date(2026, 4, 6), "Easter Monday"),
    (date(2026, 4, 27), "Anzac Day (observed)"),
    (date(2026, 6, 1), "King's Birthday"),
    (date(2026, 7, 10), "Matariki"),
    (date(2026, 10, 26), "Labour Day"),
    (date(2026, 12, 25), "Christmas Day"),
    (date(2026, 12, 28), "Boxing Day (observed)"),
    # 2027
    (date(2027, 1, 1), "New Year's Day"),
    (date(2027, 1, 4), "Day after New Year's Day (observed)"),
    (date(2027, 2, 1), "Auckland Anniversary Day"),
    (date(2027, 2, 8), "Waitangi Day (observed)"),
    (date(2027, 3, 26), "Good Friday"),
    (date(2027, 3, 29), "Easter Monday"),
    (date(2027, 4, 26), "Anzac Day (observed)"),
    (date(2027, 6, 7), "King's Birthday"),
    (date(2027, 6, 25), "Matariki"),
    (date(2027, 10, 25), "Labour Day"),
    (date(2027, 12, 27), "Christmas Day (observed)"),
    (date(2027, 12, 28), "Boxing Day (observed)"),
)

# Awaiting client confirmation (ask whether perishable food is wanted at all).
CATEGORY_NAMES: tuple[str, ...] = (
    "Clothing and textiles",
    "Electronics (e-waste)",
    "Non-perishable food",
    "Household items",
    "Books, toys and games",
    "Other",
)

# --------------------------------------------------------------------------------------
# Demo accounts. Passwords come from the environment (see app.config), never from here.
# --------------------------------------------------------------------------------------
DEMO_ADMIN: tuple[str, str] = ("admin@koharoute.test", "Demo Admin")
DEMO_DRIVERS: tuple[tuple[str, str], ...] = (
    ("driver1@koharoute.test", "Demo Driver 1"),
    ("driver2@koharoute.test", "Demo Driver 2"),
    ("driver3@koharoute.test", "Demo Driver 3"),
)


@dataclass(frozen=True)
class DemoVehicle:
    """A placeholder vehicle. Capacities are awaiting client confirmation."""

    name: str
    plate_number: str
    capacity_kg: int
    capacity_litres: int


DEMO_VEHICLES: tuple[DemoVehicle, ...] = (
    DemoVehicle("Demo Van", "KOHA01", 600, 3000),
    DemoVehicle("Demo Ute", "KOHA02", 300, 1500),
)


@dataclass(frozen=True)
class DemoBooking:
    """A fictional booking. ``open_day_index`` 0 means the next open day after today."""

    reference: str
    donor_name: str
    contact_number: str
    address_text: str
    latitude: float
    longitude: float
    open_day_index: int
    size: str
    quantity: int
    category_names: tuple[str, ...]
    status: BookingStatus
    description: str | None = None
    rejection_reason: str | None = None


# Six Approved bookings on the next open day (a realistic day to plan a route for), then
# Pending bookings on later days and one Rejected booking. Locations are suburb centres.
# The formatter is switched off for this table: one booking per row reads better than
# one value per line.
# fmt: off
DEMO_BOOKINGS: tuple[DemoBooking, ...] = (
    DemoBooking(
        "KR-DEMO-01", "Demo Donor 1", "021 555 0101", "12 Sample Road, Henderson, Auckland",
        -36.8795, 174.6340, 0, "medium", 2, ("Clothing and textiles",), BookingStatus.APPROVED,
    ),
    DemoBooking(
        "KR-DEMO-02", "Demo Donor 2", "021 555 0102", "34 Sample Street, Te Atatu, Auckland",
        -36.8490, 174.6570, 0, "large", 1, ("Household items",), BookingStatus.APPROVED,
        description="A small bookcase and a box of kitchenware.",
    ),
    DemoBooking(
        "KR-DEMO-03", "Demo Donor 3", "021 555 0103", "5 Sample Avenue, Glen Eden, Auckland",
        -36.9080, 174.6490, 0, "small", 3, ("Books, toys and games",), BookingStatus.APPROVED,
    ),
    DemoBooking(
        "KR-DEMO-04", "Demo Donor 4", "021 555 0104", "78 Sample Lane, New Lynn, Auckland",
        -36.9070, 174.6860, 0, "medium", 1, ("Non-perishable food",), BookingStatus.APPROVED,
    ),
    DemoBooking(
        "KR-DEMO-05", "Demo Donor 5", "021 555 0105", "9 Sample Place, Kumeu, Auckland",
        -36.7790, 174.5690, 0, "large", 2, ("Household items", "Other"), BookingStatus.APPROVED,
    ),
    DemoBooking(
        "KR-DEMO-06", "Demo Donor 6", "021 555 0106", "21 Sample Drive, Hobsonville, Auckland",
        -36.7890, 174.6520, 0, "small", 2, ("Electronics (e-waste)",), BookingStatus.APPROVED,
    ),
    DemoBooking(
        "KR-DEMO-07", "Demo Donor 7", "021 555 0107", "3 Sample Close, Massey, Auckland",
        -36.8300, 174.6330, 1, "medium", 1, ("Clothing and textiles", "Books, toys and games"),
        BookingStatus.PENDING,
    ),
    DemoBooking(
        "KR-DEMO-08", "Demo Donor 8", "021 555 0108", "66 Sample Way, Swanson, Auckland",
        -36.8560, 174.5870, 1, "small", 1, ("Other",), BookingStatus.PENDING,
    ),
    DemoBooking(
        "KR-DEMO-09", "Demo Donor 9", "021 555 0109", "40 Sample Terrace, Avondale, Auckland",
        -36.8960, 174.6970, 2, "large", 1, ("Household items",), BookingStatus.PENDING,
    ),
    DemoBooking(
        "KR-DEMO-10", "Demo Donor 10", "021 555 0110", "15 Sample Grove, Albany, Auckland",
        -36.7270, 174.7050, 1, "medium", 4, ("Non-perishable food",), BookingStatus.REJECTED,
        rejection_reason="The items are damaged and cannot be passed on.",
    ),
)
# fmt: on
