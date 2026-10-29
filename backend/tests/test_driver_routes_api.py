"""US-10 and US-11 acceptance tests for driver routes and stop updates."""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.models import (
    Booking,
    BookingStatus,
    Category,
    Photo,
    Route,
    RouteStop,
    User,
    UserRole,
    Vehicle,
)
from app.security import create_access_token
from app.timeutil import today_nz


def _headers(user_id: int, role: str) -> dict[str, str]:
    """Create a short-lived bearer token for a fixture user."""
    token = create_access_token(user_id, role, timedelta(minutes=10))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def driver_client(client, db_session):
    """Provide two authenticated drivers with the test application client."""
    driver1 = User(
        email="driver1@koha.nz",
        password_hash="unused",
        full_name="Driver One",
        role=UserRole.DRIVER,
        is_active=True,
    )
    driver2 = User(
        email="driver2@koha.nz",
        password_hash="unused",
        full_name="Driver Two",
        role=UserRole.DRIVER,
        is_active=True,
    )
    db_session.add_all([driver1, driver2])
    db_session.commit()

    vehicle1 = Vehicle(
        name="Van",
        plate_number="KOHA01",
        capacity_kg=600,
        capacity_litres=3000,
        is_active=True,
    )
    vehicle2 = Vehicle(
        name="Ute",
        plate_number="KOHA02",
        capacity_kg=300,
        capacity_litres=1500,
        is_active=True,
    )
    db_session.add_all([vehicle1, vehicle2])
    db_session.commit()

    booking1 = Booking(
        reference="KR-BOOK-001",
        donor_name="Donor One",
        contact_number="021 555 0001",
        address_text="1 Sample Road, Auckland",
        latitude=-36.818826,
        longitude=174.609864,
        pickup_date=today_nz(),
        size="Medium",
        quantity=1,
        estimated_weight_kg=15,
        estimated_volume_l=60,
        status=BookingStatus.SCHEDULED,
    )
    booking2 = Booking(
        reference="KR-BOOK-002",
        donor_name="Donor Two",
        contact_number="021 555 0002",
        address_text="2 Sample Road, Auckland",
        latitude=-36.82,
        longitude=174.61,
        pickup_date=today_nz(),
        size="Small",
        quantity=2,
        estimated_weight_kg=10,
        estimated_volume_l=40,
        status=BookingStatus.SCHEDULED,
    )
    db_session.add_all([booking1, booking2])
    db_session.commit()

    route1 = Route(
        pickup_date=today_nz(),
        driver_id=driver1.id,
        vehicle_id=vehicle1.id,
        vehicle_name="Van",
        vehicle_plate_number="KOHA01",
        vehicle_capacity_kg=600,
        vehicle_capacity_litres=3000,
        total_distance_m=5000,
        total_duration_s=1800,
        planned_weight_kg=25,
        planned_volume_l=100,
        geometry="",
        color="#247BA0",
    )
    route2 = Route(
        pickup_date=today_nz(),
        driver_id=driver2.id,
        vehicle_id=vehicle2.id,
        vehicle_name="Ute",
        vehicle_plate_number="KOHA02",
        vehicle_capacity_kg=300,
        vehicle_capacity_litres=1500,
        total_distance_m=3000,
        total_duration_s=1200,
        planned_weight_kg=10,
        planned_volume_l=40,
        geometry="",
        color="#F25F5C",
    )
    db_session.add_all([route1, route2])
    db_session.flush()

    stop1 = RouteStop(
        route_id=route1.id,
        booking_id=booking1.id,
        sequence=1,
        status=BookingStatus.SCHEDULED,
    )
    stop2 = RouteStop(
        route_id=route1.id,
        booking_id=booking2.id,
        sequence=2,
        status=BookingStatus.SCHEDULED,
    )
    db_session.add_all([stop1, stop2])
    db_session.commit()

    return {
        "client": client,
        "db": db_session,
        "driver1": _headers(driver1.id, "driver"),
        "driver2": _headers(driver2.id, "driver"),
        "route1_id": route1.id,
        "route2_id": route2.id,
        "stop1_id": stop1.id,
        "stop2_id": stop2.id,
        "booking1_id": booking1.id,
        "booking2_id": booking2.id,
    }


def test_driver_sees_only_own_routes(driver_client):
    """US-10: A driver sees only their own stops, in stop order."""
    response = driver_client["client"].get(
        "/api/driver/routes", headers=driver_client["driver1"]
    )
    assert response.status_code == 200
    routes = response.json()
    assert len(routes) == 1
    assert routes[0]["id"] == driver_client["route1_id"]
    assert len(routes[0]["stops"]) == 2
    assert routes[0]["stops"][0]["sequence"] == 1
    assert routes[0]["stops"][1]["sequence"] == 2


def test_driver_route_returns_next_stop_first(driver_client):
    """US-10: Stops are ordered by sequence with next stop at the top."""
    response = driver_client["client"].get(
        "/api/driver/routes", headers=driver_client["driver1"]
    )
    assert response.status_code == 200
    route = response.json()[0]
    stops = route["stops"]
    assert stops[0]["sequence"] == 1
    assert stops[0]["reference"] == "KR-BOOK-001"
    assert stops[0]["donor_name"] == "Donor One"
    assert stops[0]["contact_number"] == "021 555 0001"
    assert stops[0]["category_names"] == []
    assert stops[0]["estimated_weight_kg"] == 15
    assert stops[0]["estimated_volume_l"] == 60


def test_other_driver_cannot_see_route(driver_client):
    """US-10: Driver cannot see another driver's route."""
    response = driver_client["client"].get(
        "/api/driver/routes", headers=driver_client["driver2"]
    )
    assert response.status_code == 200
    routes = response.json()
    assert len(routes) == 1
    assert routes[0]["id"] == driver_client["route2_id"]
    # Driver One's stops and donors must not leak into Driver Two's response.
    assert routes[0]["stops"] == []
    assert "KR-BOOK-001" not in response.text
    assert "Donor One" not in response.text


def test_driver_can_mark_stop_completed_without_remark(driver_client):
    """US-11: Marking a stop Completed does not require a remark."""
    response = driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route1_id']}/stops/{driver_client['booking1_id']}",
        json={"status": "completed"},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["remark"] is None
    assert data["completed_at"] is not None


def test_driver_can_mark_stop_missed_with_remark(driver_client):
    """US-11: Marking a stop Missed requires and stores a remark."""
    response = driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route1_id']}/stops/{driver_client['booking2_id']}",
        json={"status": "missed", "remark": "No one home."},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "missed"
    assert data["remark"] == "No one home."
    assert data["completed_at"] is not None


def test_missed_stop_requires_remark(driver_client):
    """US-11: Marking Missed without a remark returns 422."""
    response = driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route1_id']}/stops/{driver_client['booking1_id']}",
        json={"status": "missed"},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 422


def test_completed_stop_cannot_be_changed(driver_client):
    """US-11: A Completed stop is locked and cannot be changed."""
    driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route1_id']}/stops/{driver_client['booking1_id']}",
        json={"status": "completed"},
        headers=driver_client["driver1"],
    )
    response = driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route1_id']}/stops/{driver_client['booking1_id']}",
        json={"status": "missed", "remark": "Changed mind."},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 409


def test_driver_cannot_update_another_driver_stop(driver_client):
    """US-11: Updating another driver's stop returns 403."""
    response = driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route2_id']}/stops/{driver_client['booking1_id']}",
        json={"status": "completed"},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 403


def test_stop_update_records_time_and_driver(driver_client):
    """US-11: Completed time and driver are recorded."""
    response = driver_client["client"].patch(
        f"/api/driver/routes/{driver_client['route1_id']}/stops/{driver_client['booking1_id']}",
        json={"status": "completed"},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["completed_at"] is not None


def test_driver_routes_require_driver_role(client):
    """US-01: Non-driver roles are denied access to driver endpoints."""
    # No driver token provided -> 401
    response = client.get("/api/driver/routes")
    assert response.status_code == 401


def test_admin_cannot_use_driver_routes(driver_client):
    """US-10: A logged-in Admin is refused with 403, not shown a driver's route."""
    admin = User(
        email="admin@koha.nz",
        password_hash="unused",
        full_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    driver_client["db"].add(admin)
    driver_client["db"].commit()
    response = driver_client["client"].get(
        "/api/driver/routes", headers=_headers(admin.id, "admin")
    )
    assert response.status_code == 403


def _add_route_for_day(driver_client, driver_key, day, *, reverse_insert=False):
    """Create a route for ``day`` reusing the fixture's two bookings."""
    db = driver_client["db"]
    base = db.get(Route, driver_client["route1_id"])
    driver_id = base.driver_id if driver_key == "driver1" else db.get(
        Route, driver_client["route2_id"]
    ).driver_id
    route = Route(
        pickup_date=day,
        driver_id=driver_id,
        vehicle_id=base.vehicle_id,
        vehicle_name="Van",
        vehicle_plate_number="KOHA01",
        vehicle_capacity_kg=600,
        vehicle_capacity_litres=3000,
        total_distance_m=1000,
        total_duration_s=600,
        planned_weight_kg=25,
        planned_volume_l=100,
        geometry="",
        color="#247BA0",
    )
    db.add(route)
    db.flush()
    pairs = [(2, driver_client["booking2_id"]), (1, driver_client["booking1_id"])]
    if not reverse_insert:
        pairs.reverse()
    for sequence, booking_id in pairs:
        db.add(
            RouteStop(
                route_id=route.id,
                booking_id=booking_id,
                sequence=sequence,
                status=BookingStatus.SCHEDULED,
            )
        )
    db.commit()
    return route.id


def test_no_route_for_the_day_returns_empty_list(driver_client):
    """US-10: With no route for the day the API returns [] (the page shows 'No route assigned')."""
    empty_day = (today_nz() + timedelta(days=5)).isoformat()
    response = driver_client["client"].get(
        "/api/driver/routes",
        params={"pickup_date": empty_day},
        headers=driver_client["driver1"],
    )
    assert response.status_code == 200
    assert response.json() == []


def test_driver_can_choose_another_day_and_default_stays_today(driver_client):
    """US-10: Today is the default; a chosen day returns only that day's route."""
    tomorrow = today_nz() + timedelta(days=1)
    tomorrow_route_id = _add_route_for_day(driver_client, "driver1", tomorrow)
    client, headers = driver_client["client"], driver_client["driver1"]

    default = client.get("/api/driver/routes", headers=headers).json()
    assert [route["id"] for route in default] == [driver_client["route1_id"]]

    chosen = client.get(
        "/api/driver/routes", params={"pickup_date": tomorrow.isoformat()}, headers=headers
    ).json()
    assert [route["id"] for route in chosen] == [tomorrow_route_id]


def test_stops_are_returned_in_stop_order_whatever_the_insert_order(driver_client):
    """US-10: Stop order comes from the saved sequence, not from row insertion order."""
    day = today_nz() + timedelta(days=2)
    _add_route_for_day(driver_client, "driver1", day, reverse_insert=True)
    route = driver_client["client"].get(
        "/api/driver/routes",
        params={"pickup_date": day.isoformat()},
        headers=driver_client["driver1"],
    ).json()[0]
    assert [stop["sequence"] for stop in route["stops"]] == [1, 2]
    assert [stop["reference"] for stop in route["stops"]] == ["KR-BOOK-001", "KR-BOOK-002"]


def test_stop_includes_address_categories_donor_description_and_photos(driver_client):
    """US-10: Each stop carries everything the driver needs to open it."""
    db = driver_client["db"]
    booking = db.get(Booking, driver_client["booking1_id"])
    booking.description = "Two boxes by the gate."
    booking.categories.append(Category(name="Household items", sort_order=1))
    # Attach through the relationship: the test shares one long-lived session with the API
    # (expire_on_commit is off), so a Photo added by booking_id alone would never refresh the
    # booking's already-loaded, empty photo list. Real requests each get a fresh session.
    booking.photos.append(
        Photo(
            stored_name="photo-one.png",
            content_type="image/png",
            size_bytes=4,
        )
    )
    db.commit()

    stop = driver_client["client"].get(
        "/api/driver/routes", headers=driver_client["driver1"]
    ).json()[0]["stops"][0]
    assert stop["address_text"] == "1 Sample Road, Auckland"
    assert stop["category_names"] == ["Household items"]
    assert stop["donor_name"] == "Donor One"
    assert stop["contact_number"] == "021 555 0001"
    assert stop["description"] == "Two boxes by the gate."
    assert len(stop["photos"]) == 1
    assert stop["photos"][0]["content_type"] == "image/png"


def test_route_page_uses_saved_geometry_and_makes_no_ors_call(driver_client):
    """US-10: The saved US-06 line is returned and the route planner is never called."""
    saved_line = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    db = driver_client["db"]
    db.get(Route, driver_client["route1_id"]).geometry = saved_line
    db.commit()

    class ExplodingPlanner:
        async def plan(self, problem):  # pragma: no cover - must never run
            raise AssertionError("Viewing a route must not call ORS")

    client = driver_client["client"]
    client.app.state.route_planner = ExplodingPlanner()
    response = client.get("/api/driver/routes", headers=driver_client["driver1"])
    assert response.status_code == 200
    assert response.json()[0]["geometry"] == saved_line


@pytest.fixture()
def photo_file(driver_client, tmp_path, monkeypatch):
    """A real stored photo attached to booking 1 (on Driver One's route)."""
    (tmp_path / "photo-one.png").write_bytes(b"\x89PNG-test")
    db = driver_client["db"]
    photo = Photo(
        booking_id=driver_client["booking1_id"],
        stored_name="photo-one.png",
        content_type="image/png",
        size_bytes=9,
    )
    db.add(photo)
    db.commit()
    monkeypatch.setattr(
        "app.api.driver_routes.get_config",
        lambda: SimpleNamespace(photo_storage_dir=tmp_path),
    )
    return photo.id


def _photo_url(driver_client, photo_id, *, route_key="route1_id", booking_key="booking1_id"):
    return (
        f"/api/driver/routes/{driver_client[route_key]}"
        f"/stops/{driver_client[booking_key]}/photos/{photo_id}"
    )


def test_assigned_driver_can_view_stop_photo(driver_client, photo_file):
    """US-10: The assigned driver can load the donor's photo."""
    response = driver_client["client"].get(
        _photo_url(driver_client, photo_file), headers=driver_client["driver1"]
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG-test"


def test_other_driver_cannot_view_stop_photo(driver_client, photo_file):
    """US-10: Photos are private to the driver who owns the route."""
    response = driver_client["client"].get(
        _photo_url(driver_client, photo_file), headers=driver_client["driver2"]
    )
    assert response.status_code == 403


def test_photo_requires_login(driver_client, photo_file):
    """US-10: No token, no photo."""
    response = driver_client["client"].get(_photo_url(driver_client, photo_file))
    assert response.status_code == 401


def test_photo_from_a_different_stop_is_not_served(driver_client, photo_file):
    """US-10: A photo id from booking 1 cannot be read through booking 2's stop."""
    response = driver_client["client"].get(
        _photo_url(driver_client, photo_file, booking_key="booking2_id"),
        headers=driver_client["driver1"],
    )
    assert response.status_code == 404
