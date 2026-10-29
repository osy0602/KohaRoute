"""US-04 acceptance tests for Admin booking review and transitions."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from app.services.booking_rules import available_booking_dates

import pytest

from app.models import Booking, BookingStatus, Category, Photo, User, UserRole
from app.security import create_access_token
from app.seed import seed_closed_dates, seed_settings
from app.services.booking_rules import available_booking_dates


def auth_headers(user_id: int, role: str) -> dict[str, str]:
    """Make an authenticated request header for a test staff role."""
    token = create_access_token(user_id, role, timedelta(minutes=15))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def staff_client(client, db_session):
    """Provide Admin and driver credentials against the in-memory test database."""
    admin = User(
        email="admin-review@koha.nz",
        password_hash="not-used-by-auth-dependency",
        full_name="Review Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    driver = User(
        email="driver-review@koha.nz",
        password_hash="not-used-by-auth-dependency",
        full_name="Review Driver",
        role=UserRole.DRIVER,
        is_active=True,
    )
    db_session.add_all([admin, driver])
    db_session.commit()
    return {
        "client": client,
        "db": db_session,
        "admin": auth_headers(admin.id, "admin"),
        "driver": auth_headers(driver.id, "driver"),
    }


def add_booking(db, reference, pickup_date, status=BookingStatus.PENDING, category=None):
    """Insert a representative booking with personal details for access-control tests."""
    booking = Booking(
        reference=reference,
        donor_name="Aroha Donor",
        contact_number="021 555 0101",
        address_text="11 Kohuhu Lane, Westgate, Auckland",
        latitude=-36.818826,
        longitude=174.609864,
        pickup_date=pickup_date,
        size="medium",
        quantity=2,
        estimated_weight_kg=30,
        estimated_volume_l=120,
        description="Two boxes of household items.",
        status=status,
        categories=[category] if category else [],
    )
    db.add(booking)
    db.flush()
    return booking


@pytest.fixture()
def review_data(staff_client):
    """Create categories, business calendar, and bookings in several states/dates."""
    db = staff_client["db"]
    seed_settings(db)
    seed_closed_dates(db)
    category = Category(name="Review category", sort_order=0)
    db.add(category)
    db.flush()
    pending = add_booking(db, "KR-ADMIN-PENDING", date(2026, 10, 20), category=category)
    approved = add_booking(
        db,
        "KR-ADMIN-APPROVED",
        date(2026, 10, 21),
        BookingStatus.APPROVED,
        category,
    )
    missed = add_booking(
        db,
        "KR-ADMIN-MISSED",
        date(2026, 10, 22),
        BookingStatus.MISSED,
        category,
    )
    rejected = add_booking(
        db,
        "KR-ADMIN-REJECTED",
        date(2026, 10, 20),
        BookingStatus.REJECTED,
        category,
    )
    rejected.rejection_reason = "The items cannot be accepted."
    photo = Photo(
        booking_id=pending.id,
        stored_name="private-admin-photo.png",
        content_type="image/png",
        size_bytes=4,
    )
    db.add(photo)
    db.commit()
    return {"pending": pending, "approved": approved, "missed": missed, "rejected": rejected}


def test_admin_list_defaults_to_pending_and_includes_review_fields(staff_client, review_data):
    """Default list shows Pending items, estimates, categories, and photo metadata."""
    response = staff_client["client"].get("/api/admin/bookings", headers=staff_client["admin"])
    assert response.status_code == 200
    rows = response.json()
    assert [row["reference"] for row in rows] == ["KR-ADMIN-PENDING"]
    assert rows[0]["donor_name"] == "Aroha Donor"
    assert rows[0]["address_text"] == "11 Kohuhu Lane, Westgate, Auckland"
    assert rows[0]["category_names"] == ["Review category"]
    assert (rows[0]["estimated_weight_kg"], rows[0]["estimated_volume_l"]) == (30, 120)
    assert len(rows[0]["photos"]) == 1


def test_admin_list_filters_by_status_and_pickup_date(staff_client, review_data):
    """Admin can filter a list by status and pickup date independently or together."""
    client = staff_client["client"]
    headers = staff_client["admin"]
    approved = client.get("/api/admin/bookings?status=approved", headers=headers)
    assert [row["reference"] for row in approved.json()] == ["KR-ADMIN-APPROVED"]
    date_filtered = client.get(
        "/api/admin/bookings?status=all&pickup_date=2026-10-20", headers=headers
    )
    assert {row["reference"] for row in date_filtered.json()} == {
        "KR-ADMIN-PENDING",
        "KR-ADMIN-REJECTED",
    }


def test_driver_and_anonymous_users_cannot_access_admin_api(staff_client, review_data):
    """Every Admin review endpoint is protected by a server-side role check."""
    client = staff_client["client"]
    assert client.get("/api/admin/bookings").status_code == 401
    assert client.get("/api/admin/bookings", headers=staff_client["driver"]).status_code == 403
    booking_id = review_data["pending"].id
    response = client.post(
        f"/api/admin/bookings/{booking_id}/approve", headers=staff_client["driver"]
    )
    assert response.status_code == 403


def test_admin_detail_includes_full_booking_fields_and_coordinates(staff_client, review_data):
    """Admin detail includes description, contact, complete address, and map coordinates."""
    booking_id = review_data["pending"].id
    response = staff_client["client"].get(
        f"/api/admin/bookings/{booking_id}", headers=staff_client["admin"]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contact_number"] == "021 555 0101"
    assert body["description"] == "Two boxes of household items."
    # The size preset and quantity behind the estimate are shown to the Admin (US-04).
    assert body["size"] == "medium"
    assert body["quantity"] == 2
    assert body["latitude"] == pytest.approx(-36.818826)
    assert body["longitude"] == pytest.approx(174.609864)


def test_approve_is_pending_only(staff_client, review_data):
    """Approval transitions Pending to Approved and is not offered for other states."""
    client = staff_client["client"]
    headers = staff_client["admin"]
    pending_id = review_data["pending"].id
    approved = client.post(f"/api/admin/bookings/{pending_id}/approve", headers=headers)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    repeated_approval = client.post(f"/api/admin/bookings/{pending_id}/approve", headers=headers)
    assert repeated_approval.status_code == 409


def test_rejection_requires_a_nonblank_reason(staff_client, review_data):
    """Rejection without a meaningful reason is blocked; a valid reason is saved."""
    client = staff_client["client"]
    headers = staff_client["admin"]
    booking_id = review_data["pending"].id
    assert (
        client.post(
            f"/api/admin/bookings/{booking_id}/reject", json={}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/admin/bookings/{booking_id}/reject",
            json={"reason": "   "},
            headers=headers,
        ).status_code
        == 422
    )
    rejected = client.post(
        f"/api/admin/bookings/{booking_id}/reject",
        json={"reason": "  Not suitable for collection.  "},
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejection_reason"] == "Not suitable for collection."


def test_reschedule_approved_or_missed_to_an_open_day(staff_client, review_data):
    """Approved and Missed bookings are moved to an open date and return to Approved."""
    client = staff_client["client"]
    headers = staff_client["admin"]
    open_day = available_booking_dates(staff_client["db"]).earliest.isoformat()
    for key in ("approved", "missed"):
        booking_id = review_data[key].id
        response = client.post(
            f"/api/admin/bookings/{booking_id}/reschedule",
            json={"pickup_date": open_day},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        assert response.json()["pickup_date"] == open_day


def test_pending_booking_cannot_be_rescheduled(staff_client, review_data):
    """Rescheduling is only legal from Approved or Missed."""
    response = staff_client["client"].post(
        f"/api/admin/bookings/{review_data['pending'].id}/reschedule",
        json={"pickup_date": "2026-10-20"},
        headers=staff_client["admin"],
    )
    assert response.status_code == 409


def test_admin_photo_route_serves_file_and_rejects_other_bookings(
    staff_client, review_data, monkeypatch, tmp_path
):
    """Private photos are served only to Admins and only through the owning booking."""
    photo = review_data["pending"].photos[0]
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    photo_path = photo_dir / photo.stored_name
    photo_path.write_bytes(b"image")
    monkeypatch.setattr(
        "app.api.admin_bookings.get_config",
        lambda: SimpleNamespace(photo_storage_dir=Path(photo_dir)),
    )
    client = staff_client["client"]
    url = f"/api/admin/bookings/{review_data['pending'].id}/photos/{photo.id}"
    served = client.get(url, headers=staff_client["admin"])
    assert served.status_code == 200
    assert served.content == b"image"
    assert served.headers["content-type"] == "image/png"
    assert client.get(url, headers=staff_client["driver"]).status_code == 403
    assert (
        client.get(
            f"/api/admin/bookings/{review_data['approved'].id}/photos/{photo.id}",
            headers=staff_client["admin"],
        ).status_code
        == 404
    )
