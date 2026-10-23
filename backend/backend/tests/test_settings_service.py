from datetime import time

import pytest

from app.models import SettingKey
from app.seed import seed_closed_dates, seed_settings
from app.services.settings_service import (
    MissingSettingError,
    load_business_settings,
    load_closed_dates,
    upsert_setting,
)


@pytest.fixture()
def seeded(db_session):
    seed_settings(db_session)
    seed_closed_dates(db_session)
    return db_session


def test_opening_hours_and_days(seeded):
    settings = load_business_settings(seeded)
    assert settings.opening_days == (0, 1, 2, 3, 4)  # Monday to Friday
    assert settings.opening_time == time(9, 0)
    assert settings.closing_time == time(17, 0)


def test_booking_limits(seeded):
    settings = load_business_settings(seeded)
    assert settings.booking_window_days == 7
    assert settings.max_quantity == 10
    assert (settings.min_photos, settings.max_photos) == (1, 3)
    assert settings.max_photo_bytes == 5 * 1024 * 1024
    assert settings.description_max_chars == 300
    assert settings.session_minutes == 480


def test_size_presets_match_the_agreed_values(seeded):
    loaded = load_business_settings(seeded).size_presets
    presets = {preset.key: (preset.weight_kg, preset.volume_l) for preset in loaded}
    assert presets == {"small": (5, 20), "medium": (15, 60), "large": (30, 150)}


def test_estimate_is_preset_times_quantity(seeded):
    estimate = load_business_settings(seeded).size_preset("medium").estimate(3)
    assert (estimate.weight_kg, estimate.volume_l) == (45, 180)


def test_estimate_rejects_quantity_below_one(seeded):
    with pytest.raises(ValueError, match="at least 1"):
        load_business_settings(seeded).size_preset("small").estimate(0)


def test_unknown_size_is_reported(seeded):
    with pytest.raises(KeyError, match="huge"):
        load_business_settings(seeded).size_preset("huge")


def test_depot_is_in_westgate_and_not_yet_geocoded(seeded):
    depot = load_business_settings(seeded).depot
    assert "Westgate" in depot.address
    assert depot.is_geocoded is False
    assert -37.0 < depot.latitude < -36.7
    assert 174.4 < depot.longitude < 174.8


def test_missing_settings_explain_how_to_fix_it(db_session):
    with pytest.raises(MissingSettingError, match="python -m app.seed"):
        load_business_settings(db_session)


def test_upsert_replaces_an_existing_value(seeded):
    upsert_setting(seeded, SettingKey.BOOKING_WINDOW_DAYS, 14)
    seeded.flush()
    assert load_business_settings(seeded).booking_window_days == 14


def test_closed_dates_load_as_a_set(seeded):
    closed = load_closed_dates(seeded)
    assert len(closed) == 24
