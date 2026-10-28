"""US-05 acceptance tests for Admin vehicle management."""

from datetime import timedelta

import pytest

from app.models import User, UserRole, Vehicle
from app.security import create_access_token
from app.services.vehicle_service import (
    VehicleInUseError,
    ensure_vehicle_not_on_active_route,
)


def _headers(user_id: int, role: str) -> dict[str, str]:
    """Create a short-lived bearer token for an Admin or driver fixture user."""
    token = create_access_token(user_id, role, timedelta(minutes=10))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def vehicle_client(client, db_session):
    """Provide authenticated Admin and driver headers with the test application client."""
    admin = User(
        email="vehicle-admin@koha.nz",
        password_hash="unused",
        full_name="Vehicle Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    driver = User(
        email="vehicle-driver@koha.nz",
        password_hash="unused",
        full_name="Vehicle Driver",
        role=UserRole.DRIVER,
        is_active=True,
    )
    db_session.add_all([admin, driver])
    db_session.commit()
    return {
        "client": client,
        "db": db_session,
        "admin": _headers(admin.id, "admin"),
        "driver": _headers(driver.id, "driver"),
    }


def test_vehicle_endpoints_require_admin(vehicle_client):
    """Anonymous users and drivers cannot list or modify vehicles."""
    client = vehicle_client["client"]
    assert client.get("/api/admin/vehicles").status_code == 401
    assert client.get(
        "/api/admin/vehicles", headers=vehicle_client["driver"]
    ).status_code == 403
    assert client.post(
        "/api/admin/vehicles",
        json={
            "name": "Van",
            "plate_number": "KOHA01",
            "capacity_kg": 500,
            "capacity_litres": 2000,
        },
        headers=vehicle_client["driver"],
    ).status_code == 403


def test_admin_can_create_and_list_active_vehicle(vehicle_client):
    """Creation normalizes the plate and stores the vehicle as active."""
    response = vehicle_client["client"].post(
        "/api/admin/vehicles",
        json={
            "name": "  Community Van  ",
            "plate_number": "koha01",
            "capacity_kg": 600,
            "capacity_litres": 3000,
        },
        headers=vehicle_client["admin"],
    )
    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "name": "Community Van",
        "plate_number": "KOHA01",
        "capacity_kg": 600,
        "capacity_litres": 3000,
        "is_active": True,
    }
    listed = vehicle_client["client"].get(
        "/api/admin/vehicles", headers=vehicle_client["admin"]
    )
    assert listed.status_code == 200
    assert listed.json()[0]["plate_number"] == "KOHA01"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "  "),
        ("plate_number", "TOOLONG"),
        ("plate_number", "AB-123"),
        ("capacity_kg", 0),
        ("capacity_litres", -10),
    ],
)
def test_invalid_vehicle_values_are_rejected(vehicle_client, field, value):
    """Blank names, invalid NZ plates, and non-positive capacities are refused."""
    payload = {
        "name": "Ute",
        "plate_number": "KOHA02",
        "capacity_kg": 300,
        "capacity_litres": 1500,
    }
    payload[field] = value
    response = vehicle_client["client"].post(
        "/api/admin/vehicles", json=payload, headers=vehicle_client["admin"]
    )
    assert response.status_code == 422
    assert vehicle_client["db"].query(Vehicle).count() == 0


def test_duplicate_plate_is_rejected_case_insensitively(vehicle_client):
    """Plate uniqueness applies after uppercase normalization."""
    client = vehicle_client["client"]
    payload = {
        "name": "Van",
        "plate_number": "KOHA01",
        "capacity_kg": 600,
        "capacity_litres": 3000,
    }
    assert client.post(
        "/api/admin/vehicles", json=payload, headers=vehicle_client["admin"]
    ).status_code == 201
    payload["name"] = "Second van"
    payload["plate_number"] = "koha01"
    duplicate = client.post(
        "/api/admin/vehicles", json=payload, headers=vehicle_client["admin"]
    )
    assert duplicate.status_code == 409
    assert "already assigned" in duplicate.json()["detail"]


def test_edit_vehicle_changes_current_capacity_without_deleting_record(vehicle_client):
    """Edits update capacity in place while retaining the same vehicle id and status."""
    db = vehicle_client["db"]
    vehicle = Vehicle(
        name="Van",
        plate_number="KOHA01",
        capacity_kg=600,
        capacity_litres=3000,
        is_active=True,
    )
    db.add(vehicle)
    db.commit()
    response = vehicle_client["client"].put(
        f"/api/admin/vehicles/{vehicle.id}",
        json={
            "name": "Updated van",
            "plate_number": "koha01",
            "capacity_kg": 700,
            "capacity_litres": 3500,
        },
        headers=vehicle_client["admin"],
    )
    assert response.status_code == 200
    assert response.json()["id"] == vehicle.id
    assert response.json()["name"] == "Updated van"
    assert response.json()["capacity_kg"] == 700
    assert response.json()["capacity_litres"] == 3500
    assert response.json()["is_active"] is True


def test_deactivate_marks_vehicle_inactive_without_deleting(vehicle_client):
    """Deactivation retains the row and the vehicle appears as Inactive in the list."""
    db = vehicle_client["db"]
    vehicle = Vehicle(
        name="Ute",
        plate_number="KOHA02",
        capacity_kg=300,
        capacity_litres=1500,
        is_active=True,
    )
    db.add(vehicle)
    db.commit()
    response = vehicle_client["client"].patch(
        f"/api/admin/vehicles/{vehicle.id}/deactivate",
        headers=vehicle_client["admin"],
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert db.get(Vehicle, vehicle.id) is not None
    rows = vehicle_client["client"].get(
        "/api/admin/vehicles", headers=vehicle_client["admin"]
    )
    assert rows.json()[0]["is_active"] is False


def test_active_route_conflict_is_returned_as_http_409(vehicle_client, monkeypatch):
    """The API exposes the route-assignment guard as a conflict, not an internal error."""
    vehicle = Vehicle(
        name="Van",
        plate_number="KOHA03",
        capacity_kg=600,
        capacity_litres=3000,
        is_active=True,
    )
    vehicle_client["db"].add(vehicle)
    vehicle_client["db"].commit()

    from app.models import Route
    from datetime import date
    route = Route(
        pickup_date=date.today(),
        driver_id=1,
        vehicle_id=vehicle.id,
        vehicle_name="Van",
        vehicle_plate_number="KOHA03",
        vehicle_capacity_kg=600,
        vehicle_capacity_litres=3000,
        total_distance_m=1000,
        total_duration_s=3600,
        planned_weight_kg=50,
        planned_volume_l=100,
        geometry="",
        color="#247BA0",
    )
    vehicle_client["db"].add(route)
    vehicle_client["db"].commit()

    response = vehicle_client["client"].patch(
        f"/api/admin/vehicles/{vehicle.id}/deactivate",
        headers=vehicle_client["admin"],
    )
    assert response.status_code == 409
    assert "Planned or In progress route" in response.json()["detail"]
    assert vehicle_client["db"].get(Vehicle, vehicle.id).is_active is True


@pytest.mark.parametrize("route_status", ["planned", "in_progress"])
def test_active_route_guard_blocks_deactivation(route_status):
    """The deactivation policy refuses vehicles with Planned or In progress routes."""
    with pytest.raises(VehicleInUseError, match="Planned or In progress"):
        ensure_vehicle_not_on_active_route([route_status])


@pytest.mark.parametrize("route_status", ["done", "cancelled"])
def test_completed_route_does_not_block_deactivation(route_status):
    """A route that is no longer active does not prevent deactivation."""
    ensure_vehicle_not_on_active_route([route_status])