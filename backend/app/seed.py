"""Seed script: creates the tables and fills them with settings, holidays and demo data.

Run from the backend folder:

    python -m app.seed                 add anything missing (safe to run again and again)
    python -m app.seed --reset         delete everything first, then seed (asks to confirm)

How reruns behave (idempotent: running twice gives the same result as running once):

* Settings are rewritten from ``app.seed_data`` each run. There is no settings screen in the
  MVP, so this script is how a rule is changed.
* Closed dates, categories, vehicles and demo bookings are only added when missing, so edits
  made through the app (for example a vehicle's capacity) are never overwritten.
* Users are only added when missing, so an existing account keeps its password.
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.config import AppConfig, get_config
from app.database import SessionLocal, create_tables, drop_tables
from app.models import Booking, Category, ClosedDate, User, UserRole, Vehicle
from app.security import hash_password
from app.seed_data import (
    CATEGORY_NAMES,
    DEFAULT_SETTINGS,
    DEMO_ADMIN,
    DEMO_BOOKINGS,
    DEMO_DRIVERS,
    DEMO_VEHICLES,
    NZ_CLOSED_DATES,
)
from app.services.calendar_service import next_open_days
from app.services.settings_service import (
    load_business_settings,
    load_closed_dates,
    upsert_setting,
)
from app.timeutil import today_nz

MIN_SEED_PASSWORD_LENGTH = 10


@dataclass
class SeedReport:
    """How many new rows each step added. All zeros means the database was already seeded."""

    closed_dates_added: int = 0
    categories_added: int = 0
    users_added: int = 0
    vehicles_added: int = 0
    bookings_added: int = 0

    def total_added(self) -> int:
        """Return the number of rows added across all steps."""
        return (
            self.closed_dates_added
            + self.categories_added
            + self.users_added
            + self.vehicles_added
            + self.bookings_added
        )


def seed_settings(db: Session) -> None:
    """Write every business setting, replacing existing values.

    Args:
        db: Open database session. The caller commits.
    """
    for key, value in DEFAULT_SETTINGS.items():
        upsert_setting(db, key, value)
    db.flush()


def seed_closed_dates(db: Session) -> int:
    """Add any public holiday that is not in the table yet.

    Args:
        db: Open database session. The caller commits.

    Returns:
        How many dates were added.
    """
    existing = load_closed_dates(db)
    missing = [(day, name) for day, name in NZ_CLOSED_DATES if day not in existing]
    db.add_all(ClosedDate(closed_on=day, name=name) for day, name in missing)
    db.flush()
    return len(missing)


def seed_categories(db: Session) -> int:
    """Add missing categories and keep their display order in line with the seed data.

    Args:
        db: Open database session. The caller commits.

    Returns:
        How many categories were added.
    """
    existing = {category.name: category for category in db.scalars(select(Category))}
    added = 0
    for position, name in enumerate(CATEGORY_NAMES):
        category = existing.get(name)
        if category is None:
            db.add(Category(name=name, sort_order=position))
            added += 1
        else:
            category.sort_order = position
    db.flush()
    return added


def _check_password(password: str, label: str) -> None:
    """Refuse weak demo passwords so a real deployment cannot start with a trivial one."""
    if len(password) < MIN_SEED_PASSWORD_LENGTH:
        raise ValueError(f"{label} must be at least {MIN_SEED_PASSWORD_LENGTH} characters")


def seed_users(db: Session, config: AppConfig) -> int:
    """Add the demo Admin and demo drivers if they do not exist.

    Args:
        db: Open database session. The caller commits.
        config: Supplies the demo passwords.

    Returns:
        How many users were added.

    Raises:
        ValueError: If a demo password is shorter than 10 characters.
    """
    _check_password(config.seed_admin_password, "SEED_ADMIN_PASSWORD")
    _check_password(config.seed_driver_password, "SEED_DRIVER_PASSWORD")

    existing = {user.email for user in db.scalars(select(User))}
    wanted = [(*DEMO_ADMIN, UserRole.ADMIN, config.seed_admin_password)]
    wanted += [(*driver, UserRole.DRIVER, config.seed_driver_password) for driver in DEMO_DRIVERS]

    added = 0
    for email, full_name, role, password in wanted:
        if email in existing:
            continue
        db.add(
            User(email=email, full_name=full_name, role=role, password_hash=hash_password(password))
        )
        added += 1
    db.flush()
    return added


def seed_vehicles(db: Session) -> int:
    """Add the placeholder vehicles if their plates are not in the table yet.

    Args:
        db: Open database session. The caller commits.

    Returns:
        How many vehicles were added.
    """
    existing = set(db.scalars(select(Vehicle.plate_number)))
    missing = [vehicle for vehicle in DEMO_VEHICLES if vehicle.plate_number not in existing]
    db.add_all(
        Vehicle(
            name=vehicle.name,
            plate_number=vehicle.plate_number,
            capacity_kg=vehicle.capacity_kg,
            capacity_litres=vehicle.capacity_litres,
        )
        for vehicle in missing
    )
    db.flush()
    return len(missing)


def seed_demo_bookings(db: Session, today: date) -> int:
    """Add demo bookings whose references are not in the table yet.

    Pickup dates are real open days counted from ``today`` the first time the bookings are
    created. Later runs leave them alone, so the dates do not shift.

    Args:
        db: Open database session. The caller commits.
        today: Today's date in New Zealand.

    Returns:
        How many bookings were added.
    """
    existing = set(db.scalars(select(Booking.reference)))
    missing = [spec for spec in DEMO_BOOKINGS if spec.reference not in existing]
    if not missing:
        return 0

    settings = load_business_settings(db)
    open_days = next_open_days(
        after=today,
        count=max(spec.open_day_index for spec in missing) + 1,
        opening_days=settings.opening_days,
        closed_dates=load_closed_dates(db),
    )
    categories = {category.name: category for category in db.scalars(select(Category))}

    for spec in missing:
        load = settings.size_preset(spec.size).estimate(spec.quantity)
        db.add(
            Booking(
                reference=spec.reference,
                donor_name=spec.donor_name,
                contact_number=spec.contact_number,
                address_text=spec.address_text,
                latitude=spec.latitude,
                longitude=spec.longitude,
                pickup_date=open_days[spec.open_day_index],
                size=spec.size,
                quantity=spec.quantity,
                estimated_weight_kg=load.weight_kg,
                estimated_volume_l=load.volume_l,
                description=spec.description,
                status=spec.status,
                rejection_reason=spec.rejection_reason,
                categories=[categories[name] for name in spec.category_names],
            )
        )
    db.flush()
    return len(missing)


def seed_database(
    db: Session, config: AppConfig | None = None, today: date | None = None
) -> SeedReport:
    """Run every seed step in one transaction: either everything is saved or nothing is.

    Args:
        db: Open database session with the tables already created.
        config: Supplies the demo passwords. Defaults to the application configuration.
        today: Date used to place demo bookings. Defaults to today in New Zealand.

    Returns:
        A report of how many rows each step added.
    """
    config = config or get_config()
    report = SeedReport()
    try:
        seed_settings(db)
        report.closed_dates_added = seed_closed_dates(db)
        report.categories_added = seed_categories(db)
        report.users_added = seed_users(db, config)
        report.vehicles_added = seed_vehicles(db)
        report.bookings_added = seed_demo_bookings(db, today or today_nz())
        db.commit()
    except Exception:
        db.rollback()
        raise
    return report


def reset_database(target_engine: Engine | None = None) -> None:
    """Delete every table and recreate it empty.

    Args:
        target_engine: Engine of the database to wipe. Defaults to the application engine.
    """
    drop_tables(target_engine)
    create_tables(target_engine)


def build_parser() -> argparse.ArgumentParser:
    """Describe the command-line options."""
    parser = argparse.ArgumentParser(
        prog="python -m app.seed", description="Create and fill the KohaRoute database."
    )
    parser.add_argument(
        "--reset", action="store_true", help="delete ALL data first, then seed from scratch"
    )
    parser.add_argument("--yes", action="store_true", help="skip the confirmation for --reset")
    return parser


def _confirm_reset() -> bool:
    """Ask the person to type "yes" before deleting everything."""
    answer = input("This deletes ALL data in the database. Type 'yes' to continue: ")
    return answer.strip().lower() == "yes"


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv``.

    Returns:
        Process exit code: 0 on success, 1 if the person declined the reset.
    """
    args = build_parser().parse_args(argv)

    if args.reset:
        if not args.yes and not _confirm_reset():
            print("Cancelled. Nothing was changed.")
            return 1
        reset_database()
    else:
        create_tables()

    with SessionLocal() as session:
        report = seed_database(session)

    print(f"Seed finished. Rows added: {report.total_added()}")
    print(f"  closed dates: {report.closed_dates_added}, categories: {report.categories_added}")
    print(f"  users: {report.users_added}, vehicles: {report.vehicles_added}")
    print(f"  demo bookings: {report.bookings_added}")
    if report.total_added() == 0:
        print("The database was already seeded, so nothing changed.")
    print("Demo logins: admin@koharoute.test and driver1/2/3@koharoute.test")
    print("Passwords come from SEED_ADMIN_PASSWORD and SEED_DRIVER_PASSWORD (demo use only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
