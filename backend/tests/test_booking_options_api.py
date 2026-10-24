"""API tests for the public donor form options and address autocomplete."""

import asyncio
from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import select, text

from app.api.bookings import get_address_rate_limiter, get_address_search
from app.main import app
from app.models import Category
from app.seed import seed_categories, seed_closed_dates, seed_settings
from app.services.geocoding_service import (
    AddressRateLimiter,
    AddressSearchService,
    GeocoderUnavailableError,
    verify_address_selection,
)


@pytest.fixture()
def seeded_options(db_session):
    """Add the settings, closed dates and categories returned by the form options API."""
    seed_settings(db_session)
    seed_closed_dates(db_session)
    seed_categories(db_session)
    return db_session


@pytest.fixture()
def booking_client(client, seeded_options):
    """Use the shared API test client with the seeded test database."""
    yield client


def test_booking_options_include_open_days_and_form_limits(booking_client, monkeypatch):
    """The donor form receives active categories, presets, and upload/date limits."""
    monkeypatch.setattr("app.api.bookings.available_booking_dates", lambda _db: type(
        "Window", (), {
            "dates": (date(2026, 10, 16),),
            "earliest": date(2026, 10, 16),
            "latest": date(2026, 10, 16),
        }
    )())
    response = booking_client.get("/api/bookings/options")
    assert response.status_code == 200
    body = response.json()
    assert body["pickup_dates"] == ["2026-10-16"]
    assert len(body["categories"]) == 6
    assert {preset["key"] for preset in body["size_presets"]} == {"small", "medium", "large"}
    assert (body["max_quantity"], body["min_photos"], body["max_photos"]) == (10, 1, 3)


def test_address_suggestions_return_signed_tokens(booking_client):
    """A fake provider can exercise the API without an ORS credential or network call."""

    class FakeProvider:
        async def search(self, _query):
            return [("1 Sample Road, Auckland", -36.85, 174.65)]

    app.dependency_overrides[get_address_search] = lambda: AddressSearchService(FakeProvider())
    app.dependency_overrides[get_address_rate_limiter] = lambda: AddressRateLimiter()
    try:
        response = booking_client.get(
            "/api/bookings/address-suggestions", params={"query": "sample road"}
        )
    finally:
        app.dependency_overrides.pop(get_address_search, None)
        app.dependency_overrides.pop(get_address_rate_limiter, None)
    assert response.status_code == 200
    assert response.json()[0]["label"] == "1 Sample Road, Auckland"
    assert response.json()[0]["token"]


def test_address_search_provider_failure_returns_retryable_503(booking_client):
    """ORS outages are translated into a clear retryable service response."""

    class FailingProvider:
        async def search(self, _query):
            raise GeocoderUnavailableError("Address search is unavailable. Please try again.")

    app.dependency_overrides[get_address_search] = lambda: AddressSearchService(FailingProvider())
    app.dependency_overrides[get_address_rate_limiter] = lambda: AddressRateLimiter()
    try:
        response = booking_client.get(
            "/api/bookings/address-suggestions", params={"query": "sample road"}
        )
    finally:
        app.dependency_overrides.pop(get_address_search, None)
        app.dependency_overrides.pop(get_address_rate_limiter, None)
    assert response.status_code == 503
    assert response.json()["detail"] == "Address search is unavailable. Please try again."


def test_address_suggestions_reject_short_queries(booking_client):
    """The API enforces the minimum query length even if a client ignores the UI rule."""
    response = booking_client.get("/api/bookings/address-suggestions", params={"query": "ab"})
    assert response.status_code == 422


def _photo_bytes():
    """Build a real PNG upload without depending on fixture files."""
    output = BytesIO()
    Image.new("RGB", (8, 8), "green").save(output, format="PNG")
    return output.getvalue()


class FakeAddressProvider:
    """Address provider used by donor submission tests."""

    async def search(self, _query):
        return [("1 Sample Road, Auckland", -36.85, 174.65)]


def _selected_address():
    """Get a signed address token from the same fake search service used by the form."""
    return asyncio.run(AddressSearchService(FakeAddressProvider()).suggestions("sample road"))[0]


def _booking_fields(selected, pickup_date, category_id):
    """Build a multipart form payload for one valid donor booking."""
    return {
        "donor_name": "Aroha Donor",
        "contact_number": "021 555 0101",
        "address_token": selected.token,
        "pickup_date": pickup_date.isoformat(),
        "size": "medium",
        "quantity": "2",
        "category_ids": str(category_id),
    }


def test_submit_booking_saves_estimates_and_private_photo(
    booking_client, seeded_options, monkeypatch, tmp_path
):
    """A valid donor submission becomes Pending with server-computed estimates."""
    from app.services.booking_rules import available_booking_dates

    selected = _selected_address()
    category_id = seeded_options.scalar(select(Category.id).limit(1))
    pickup_date = available_booking_dates(seeded_options).dates[0]
    photo_directory = tmp_path / "private-photos"
    monkeypatch.setattr(
        "app.api.bookings.get_config",
        lambda: SimpleNamespace(photo_storage_dir=photo_directory),
    )
    app.dependency_overrides[get_address_search] = lambda: AddressSearchService(
        FakeAddressProvider()
    )
    try:
        response = booking_client.post(
            "/api/bookings",
            data=_booking_fields(selected, pickup_date, category_id),
            files=[("photos", ("donation.png", _photo_bytes(), "image/png"))],
        )
    finally:
        app.dependency_overrides.pop(get_address_search, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["pickup_date"] == pickup_date.isoformat()
    assert (body["estimated_weight_kg"], body["estimated_volume_l"]) == (30, 120)
    assert len(body["reference"]) <= 24
    stored_files = list(photo_directory.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".png"
    assert "contact_number" not in body
    verify_address_selection(selected.token)


@pytest.mark.parametrize(
    ("field", "value", "expected_message"),
    [
        ("contact_number", "123", "New Zealand phone number"),
        ("address_token", "forged", "Select an address"),
        ("quantity", "11", "between 1 and 10"),
    ],
)
def test_invalid_booking_fields_save_nothing(
    booking_client, seeded_options, monkeypatch, tmp_path, field, value, expected_message
):
    """Invalid contact, address token, or quantity returns a field error and no file."""
    from app.services.booking_rules import available_booking_dates

    category_id = seeded_options.scalar(select(Category.id).limit(1))
    fields = _booking_fields(
        _selected_address(),
        available_booking_dates(seeded_options).dates[0],
        category_id,
    )
    fields[field] = value
    photo_directory = tmp_path / "private-photos"
    monkeypatch.setattr(
        "app.api.bookings.get_config",
        lambda: SimpleNamespace(photo_storage_dir=photo_directory),
    )
    response = booking_client.post(
        "/api/bookings",
        data=fields,
        files=[("photos", ("donation.png", _photo_bytes(), "image/png"))],
    )
    assert response.status_code == 422
    assert expected_message in response.json()["detail"]["message"]
    assert seeded_options.execute(text("SELECT count(*) FROM bookings")).scalar_one() == 0
    assert not photo_directory.exists()


def test_fourth_photo_is_rejected_before_any_booking_is_saved(
    booking_client, seeded_options, monkeypatch, tmp_path
):
    """More than the configured photo count is rejected before database or disk writes."""
    from app.services.booking_rules import available_booking_dates

    category_id = seeded_options.scalar(select(Category.id).limit(1))
    photo_directory = tmp_path / "private-photos"
    monkeypatch.setattr(
        "app.api.bookings.get_config",
        lambda: SimpleNamespace(photo_storage_dir=photo_directory),
    )
    response = booking_client.post(
        "/api/bookings",
        data=_booking_fields(
            _selected_address(),
            available_booking_dates(seeded_options).dates[0],
            category_id,
        ),
        files=[("photos", (f"{index}.png", _photo_bytes(), "image/png")) for index in range(4)],
    )
    assert response.status_code == 422
    assert "between 1 and 3" in response.json()["detail"]["message"]
    assert seeded_options.execute(text("SELECT count(*) FROM bookings")).scalar_one() == 0
    assert not photo_directory.exists()