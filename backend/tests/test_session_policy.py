"""Tests for reading the session length from the settings table."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Setting
from app.services.session_policy import (
    DEFAULT_SESSION_MINUTES,
    SESSION_MINUTES_KEY,
    get_session_minutes,
)


@pytest.fixture()
def db():
    """Give each test its own empty in-memory database."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def put_setting(db, value):
    """Store the session setting with the given raw value."""
    db.add(Setting(key=SESSION_MINUTES_KEY, value=value))
    db.commit()


def test_reads_the_value_from_settings(db):
    """A stored value of 30 means a 30 minute session."""
    put_setting(db, "30")
    assert get_session_minutes(db) == 30


def test_missing_row_falls_back_to_the_default(db):
    """No row means the 8 hour default."""
    assert get_session_minutes(db) == DEFAULT_SESSION_MINUTES


@pytest.mark.parametrize("bad_value", ["abc", "0", "-5"])
def test_invalid_value_falls_back_to_the_default(db, bad_value):
    """Text, zero and negative values are ignored."""
    put_setting(db, bad_value)
    assert get_session_minutes(db) == DEFAULT_SESSION_MINUTES
