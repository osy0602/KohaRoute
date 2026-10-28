"""Acceptance tests for the privacy-limited donor tracking endpoint (US-03)."""

from datetime import date

import pytest

from app.models import Booking, BookingStatus, Photo


@pytest.fixture()
def saved_booking(db_session):
    """Create a booking containing private fields that must not be returned publicly."""
    booking = Booking(
        reference="KR-TRACK-EXAMPLE-01",
        donor_name="Aroha Private Donor",
        contact_number="021 555 0101",
        address_text="11 Kohuhu Lane, Westgate, AU, New Zealand",
        latitude=-36.818826,
        longitude=174.609864,
        pickup_date=date(2026, 10, 20),
        size="medium",
        quantity=1,
        estimated_weight_kg=15,
        estimated_volume_l=60,
        status=BookingStatus.PENDING,
    )
    db_session.add(booking)
    db_session.flush()
    db_session.add(
        Photo(
            booking_id=booking.id,
            stored_name="private-photo.png",
            content_type="image/png",
            size_bytes=100,
        )
    )
    db_session.commit()
    return booking


def test_tracking_returns_only_public_fields(client, saved_booking):
    """Tracking omits donor name, phone, photos, and the street-level address."""
    response = client.get(f"/api/bookings/track/{saved_booking.reference}")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "pending",
        "pickup_date": "2026-10-20",
        "address_area": "Westgate",
        "rejection_reason": None,
        "missed_message": None,
    }
    serialized = response.text
    for private_value in (
        "Aroha Private Donor",
        "021 555 0101",
        "11 Kohuhu Lane",
        "private-photo.png",
    ):
        assert private_value not in serialized


@pytest.mark.parametrize(
    "booking_status",
    ["pending", "approved", "rejected", "scheduled", "completed", "missed"],
)
def test_tracking_reports_every_booking_status(client, saved_booking, db_session, booking_status):
    """The donor endpoint reports each status from the shared booking lifecycle."""
    saved_booking.status = BookingStatus(booking_status)
    db_session.commit()

    response = client.get(f"/api/bookings/track/{saved_booking.reference}")
    assert response.status_code == 200
    assert response.json()["status"] == booking_status


def test_rejected_tracking_shows_admin_reason(client, saved_booking, db_session):
    """A rejection reason is returned only for a rejected booking."""
    saved_booking.status = BookingStatus.REJECTED
    saved_booking.rejection_reason = "The items cannot be accepted."
    db_session.commit()

    response = client.get(f"/api/bookings/track/{saved_booking.reference}")
    assert response.status_code == 200
    assert response.json()["rejection_reason"] == "The items cannot be accepted."
    assert response.json()["missed_message"] is None


def test_missed_tracking_shows_rescheduling_message(client, saved_booking, db_session):
    """A missed booking tells the donor the centre will contact them to reschedule."""
    saved_booking.status = BookingStatus.MISSED
    db_session.commit()

    response = client.get(f"/api/bookings/track/{saved_booking.reference}")
    assert response.status_code == 200
    assert response.json()["missed_message"] == (
        "The centre will contact you to reschedule this pickup."
    )
    assert response.json()["rejection_reason"] is None


def test_unknown_reference_returns_no_booking_found(client):
    """Unknown references return the agreed not-found message."""
    response = client.get("/api/bookings/track/not-a-real-reference")
    assert response.status_code == 404
    assert response.json()["detail"] == "No booking found"


@pytest.mark.parametrize("reference", ["", "x" * 25])
def test_invalid_reference_length_is_rejected(client, reference):
    """Reference input is bounded before database lookup."""
    response = client.get(f"/api/bookings/track/{reference}")
    assert response.status_code in {404, 422}
