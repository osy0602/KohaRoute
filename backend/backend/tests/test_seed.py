from datetime import date

import bcrypt
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import AppConfig
from app.models import (
    Booking,
    BookingStatus,
    Category,
    ClosedDate,
    SettingKey,
    User,
    UserRole,
    Vehicle,
)
from app.seed import build_parser, reset_database, seed_database
from app.seed_data import DEMO_BOOKINGS
from app.services.calendar_service import is_open_day
from app.services.settings_service import (
    load_business_settings,
    load_closed_dates,
    upsert_setting,
)

TODAY = date(2026, 10, 15)  # a Thursday


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    monkeypatch.setattr("app.security.BCRYPT_ROUNDS", 4)


@pytest.fixture()
def config():
    return AppConfig(
        environment="test",
        database_url="sqlite://",
        cors_origins=(),
        seed_admin_password="Test-Admin-Pass-1",
        seed_driver_password="Test-Driver-Pass-1",
    )


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_first_run_creates_everything(db_session, config):
    report = seed_database(db_session, config, TODAY)
    assert report.closed_dates_added == 24
    assert report.categories_added == 6
    assert report.users_added == 4
    assert report.vehicles_added == 2
    assert report.bookings_added == len(DEMO_BOOKINGS)
    assert count(db_session, User) == 4


def test_running_twice_adds_nothing_the_second_time(db_session, config):
    seed_database(db_session, config, TODAY)
    models = (ClosedDate, Category, User, Vehicle, Booking)
    before = {model: count(db_session, model) for model in models}

    second = seed_database(db_session, config, TODAY)

    assert second.total_added() == 0
    assert before == {model: count(db_session, model) for model in models}


def test_there_is_one_admin_and_three_drivers(db_session, config):
    seed_database(db_session, config, TODAY)
    roles = [user.role for user in db_session.scalars(select(User))]
    assert roles.count(UserRole.ADMIN) == 1
    assert roles.count(UserRole.DRIVER) == 3


def test_passwords_are_hashed_with_the_configured_passwords(db_session, config):
    seed_database(db_session, config, TODAY)
    admin = db_session.scalar(select(User).where(User.role == UserRole.ADMIN))
    driver = db_session.scalar(select(User).where(User.role == UserRole.DRIVER))
    assert "Test-Admin-Pass-1" not in admin.password_hash
    assert bcrypt.checkpw(b"Test-Admin-Pass-1", admin.password_hash.encode("ascii"))
    assert bcrypt.checkpw(b"Test-Driver-Pass-1", driver.password_hash.encode("ascii"))


def test_existing_users_keep_their_passwords(db_session, config):
    seed_database(db_session, config, TODAY)
    admin = db_session.scalar(select(User).where(User.role == UserRole.ADMIN))
    admin.password_hash = "changed-by-someone"
    db_session.commit()

    seed_database(db_session, config, TODAY)

    db_session.refresh(admin)
    assert admin.password_hash == "changed-by-someone"


def test_weak_demo_password_is_refused_and_nothing_is_saved(db_session, config):
    weak = AppConfig(
        "test", "sqlite://", (), seed_admin_password="short", seed_driver_password="x" * 12
    )
    with pytest.raises(ValueError, match="SEED_ADMIN_PASSWORD"):
        seed_database(db_session, weak, TODAY)
    assert count(db_session, User) == 0
    assert count(db_session, Category) == 0


def test_reseeding_restores_settings_changed_by_hand(db_session, config):
    seed_database(db_session, config, TODAY)
    upsert_setting(db_session, SettingKey.BOOKING_WINDOW_DAYS, 99)
    db_session.commit()

    seed_database(db_session, config, TODAY)

    assert load_business_settings(db_session).booking_window_days == 7


def test_reseeding_does_not_overwrite_vehicle_edits(db_session, config):
    seed_database(db_session, config, TODAY)
    van = db_session.scalar(select(Vehicle).where(Vehicle.plate_number == "KOHA01"))
    van.capacity_kg = 750
    db_session.commit()

    seed_database(db_session, config, TODAY)

    db_session.refresh(van)
    assert van.capacity_kg == 750


def test_demo_bookings_are_on_open_days_after_today(db_session, config):
    seed_database(db_session, config, TODAY)
    settings = load_business_settings(db_session)
    closed = load_closed_dates(db_session)
    for booking in db_session.scalars(select(Booking)):
        assert booking.pickup_date > TODAY
        assert is_open_day(booking.pickup_date, settings.opening_days, closed)


def test_demo_bookings_have_estimates_and_categories(db_session, config):
    seed_database(db_session, config, TODAY)
    presets = {p.key: p for p in load_business_settings(db_session).size_presets}
    for booking in db_session.scalars(select(Booking)):
        preset = presets[booking.size]
        assert booking.estimated_weight_kg == preset.weight_kg * booking.quantity
        assert booking.estimated_volume_l == preset.volume_l * booking.quantity
        assert len(booking.categories) >= 1


def test_approved_demo_totals_match_a_manual_sum(db_session, config):
    seed_database(db_session, config, TODAY)
    approved = list(
        db_session.scalars(select(Booking).where(Booking.status == BookingStatus.APPROVED))
    )
    assert len({booking.pickup_date for booking in approved}) == 1
    assert len(approved) == 6
    assert sum(b.estimated_weight_kg for b in approved) == 160
    assert sum(b.estimated_volume_l for b in approved) == 730


def test_rejected_demo_booking_has_a_reason(db_session, config):
    seed_database(db_session, config, TODAY)
    rejected = db_session.scalars(
        select(Booking).where(Booking.status == BookingStatus.REJECTED)
    ).all()
    assert len(rejected) == 1
    assert rejected[0].rejection_reason


def test_reset_wipes_everything(db_session, config):
    seed_database(db_session, config, TODAY)
    engine = db_session.get_bind()
    db_session.close()

    reset_database(engine)

    with Session(engine) as fresh:
        assert count(fresh, User) == 0
        assert count(fresh, Booking) == 0


def test_command_line_options():
    args = build_parser().parse_args(["--reset", "--yes"])
    assert args.reset and args.yes
    args = build_parser().parse_args([])
    assert not args.reset and not args.yes
