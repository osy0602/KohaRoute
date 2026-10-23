from datetime import date

import pytest
from sqlalchemy import event, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Booking, BookingStatus, Category, Photo, User, UserRole, Vehicle


def make_booking(**overrides) -> Booking:
    values = {
        "reference": "KR-TEST-0001",
        "donor_name": "Test Donor",
        "contact_number": "021 555 0100",
        "address_text": "1 Test Street, Henderson, Auckland",
        "latitude": -36.88,
        "longitude": 174.63,
        "pickup_date": date(2026, 10, 16),
        "size": "small",
        "quantity": 1,
        "estimated_weight_kg": 5,
        "estimated_volume_l": 20,
    }
    values.update(overrides)
    return Booking(**values)


def test_all_expected_tables_exist(db_session):
    names = set(inspect(db_session.get_bind()).get_table_names())
    assert {
        "settings",
        "closed_dates",
        "categories",
        "users",
        "vehicles",
        "bookings",
        "booking_categories",
        "photos",
    } <= names


def test_booking_lookups_are_indexed(db_session):
    inspector = inspect(db_session.get_bind())
    index_names = {index["name"] for index in inspector.get_indexes("bookings")}
    assert {"ix_bookings_status_pickup_date", "ix_bookings_pickup_date"} <= index_names
    unique_columns = [c["column_names"] for c in inspector.get_unique_constraints("bookings")]
    assert ["reference"] in unique_columns
    photo_indexes = {index["name"] for index in inspector.get_indexes("photos")}
    assert "ix_photos_booking_id" in photo_indexes


def test_booking_defaults_to_pending_and_stores_readable_text(db_session):
    booking = make_booking()
    db_session.add(booking)
    db_session.flush()
    assert booking.status is BookingStatus.PENDING
    assert booking.created_at is not None
    stored = db_session.execute(text("SELECT status FROM bookings")).scalar()
    assert stored == "pending"


def test_duplicate_reference_is_refused(db_session):
    db_session.add_all([make_booking(), make_booking(donor_name="Someone Else")])
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_quantity_below_one_is_refused(db_session):
    db_session.add(make_booking(quantity=0))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_photo_cannot_point_at_a_missing_booking(db_session):
    orphan = Photo(booking_id=999, stored_name="a.jpg", content_type="image/jpeg", size_bytes=1)
    db_session.add(orphan)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_a_booking_removes_its_photos_and_category_links_only(db_session):
    category = Category(name="Other")
    booking = make_booking(categories=[category])
    booking.photos.append(
        Photo(stored_name="abc123.jpg", content_type="image/jpeg", size_bytes=1000)
    )
    db_session.add(booking)
    db_session.flush()

    db_session.delete(booking)
    db_session.flush()

    assert db_session.execute(text("SELECT COUNT(*) FROM photos")).scalar() == 0
    assert db_session.execute(text("SELECT COUNT(*) FROM booking_categories")).scalar() == 0
    assert db_session.execute(text("SELECT COUNT(*) FROM categories")).scalar() == 1


def test_listing_bookings_does_not_query_once_per_booking(db_session):
    category = Category(name="Other", sort_order=0)
    for number in range(5):
        booking = make_booking(reference=f"KR-TEST-{number:04d}", categories=[category])
        booking.photos.append(
            Photo(stored_name=f"p{number}.jpg", content_type="image/jpeg", size_bytes=1)
        )
        db_session.add(booking)
    db_session.commit()
    db_session.expire_all()

    statements = []
    engine = db_session.get_bind()

    def record(_conn, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        bookings = list(db_session.scalars(select(Booking)))
        for booking in bookings:
            assert len(booking.categories) == 1
            assert len(booking.photos) == 1
    finally:
        event.remove(engine, "before_cursor_execute", record)

    # One query for the bookings plus one each for categories and photos, however many rows.
    assert len(statements) <= 3


def test_vehicle_capacity_must_be_positive(db_session):
    db_session.add(Vehicle(name="Bad", plate_number="BAD001", capacity_kg=0, capacity_litres=100))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_vehicle_plate_is_stored_in_upper_case_and_is_unique(db_session):
    first = Vehicle(name="A", plate_number=" abc123 ", capacity_kg=100, capacity_litres=100)
    assert first.plate_number == "ABC123"
    db_session.add_all(
        [first, Vehicle(name="B", plate_number="ABC123", capacity_kg=100, capacity_litres=100)]
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_user_email_is_stored_in_lower_case_and_is_unique(db_session):
    user = User(email=" Admin@Example.COM ", password_hash="x", full_name="A", role=UserRole.ADMIN)
    assert user.email == "admin@example.com"
    duplicate = User(
        email="admin@example.com", password_hash="x", full_name="B", role=UserRole.DRIVER
    )
    db_session.add_all([user, duplicate])
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_database_refuses_an_unknown_role(db_session):
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO users (email, password_hash, full_name, role, is_active,"
                " created_at, updated_at) VALUES ('x@y.test', 'h', 'X', 'boss', 1,"
                " '2026-01-01', '2026-01-01')"
            )
        )
