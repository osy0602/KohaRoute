"""Shared pytest fixtures: a throwaway database and an API client wired to it."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import create_db_engine, get_db
from app.main import app


@pytest.fixture()
def db_session():
    """Give a test its own empty in-memory database session."""
    engine = create_db_engine("sqlite://")
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    """API client whose requests use the in-memory database instead of the real file."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
