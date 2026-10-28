"""API tests for US-01, using a private in-memory database and a fresh throttle per test."""

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import current_session_minutes, get_login_throttle
from app.api.auth import router as auth_router
from app.api.deps import require_admin
from app.database import Base, get_db
from app.main import app as main_app
from app.models import User
from app.security import create_access_token, decode_access_token, hash_password
from app.services.auth_service import INVALID_CREDENTIALS_MESSAGE
from app.services.login_throttle import LoginThrottle

PASSWORD = "demo-password-1"
TEST_SESSION_MINUTES = 45


@pytest.fixture(scope="module")
def password_hash() -> str:
    """Hash once per module: bcrypt is deliberately slow."""
    return hash_password(PASSWORD)


def make_user(email: str, role: str, is_active: bool, password_hash: str) -> User:
    """Build a user row for the test database."""
    return User(
        email=email,
        password_hash=password_hash,
        full_name=role.title(),
        role=role,
        is_active=is_active,
    )


@pytest.fixture()
def session_factory(password_hash):
    """Create an in-memory database holding an admin, a driver and a deactivated driver."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all(
            [
                make_user("admin@koha.nz", "admin", True, password_hash),
                make_user("driver@koha.nz", "driver", True, password_hash),
                make_user("gone@koha.nz", "driver", False, password_hash),
            ]
        )
        db.commit()
    return factory


@pytest.fixture()
def client(session_factory):
    """A test client on a small app: the auth router plus one Admin-only route."""
    app = FastAPI()
    app.include_router(auth_router)

    @app.get("/admin-only")
    def admin_only(_user: User = Depends(require_admin)):
        """Stand-in for a real Admin endpoint."""
        return {"ok": True}

    def override_get_db():
        """Use the in-memory database."""
        with session_factory() as db:
            yield db

    throttle = LoginThrottle(max_failures=5, window_seconds=900)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_login_throttle] = lambda: throttle
    app.dependency_overrides[current_session_minutes] = lambda: TEST_SESSION_MINUTES
    return TestClient(app)


def log_in(client, email, password=PASSWORD):
    """Post the login form."""
    return client.post("/api/auth/login", json={"email": email, "password": password})


def auth_header(token):
    """Build the Authorization header for a token."""
    return {"Authorization": f"Bearer {token}"}


def test_main_app_registers_auth_endpoints():
    """The production app exposes the endpoints defined by the auth router."""
    paths = main_app.openapi()["paths"]
    assert "post" in paths["/api/auth/login"]
    assert "get" in paths["/api/auth/me"]


def test_admin_login_returns_token_and_admin_role(client):
    """An Admin gets a token and the admin role, and no password data."""
    body = log_in(client, "admin@koha.nz").json()
    assert body["user"]["role"] == "admin"
    assert body["access_token"]
    assert "password" not in str(body).lower()


def test_driver_login_returns_driver_role(client):
    """A driver gets the driver role, which sends them to their route page."""
    assert log_in(client, "driver@koha.nz").json()["user"]["role"] == "driver"


def test_token_lasts_as_long_as_the_session_setting(client):
    """The token expiry follows the session length from settings."""
    token = log_in(client, "admin@koha.nz").json()["access_token"]
    payload = decode_access_token(token)
    assert payload["exp"] - payload["iat"] == TEST_SESSION_MINUTES * 60


def test_email_is_not_case_sensitive(client):
    """Capitals and spaces in the email do not matter."""
    assert log_in(client, "  Admin@KOHA.nz ").status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("admin@koha.nz", "wrong"),
        ("nobody@koha.nz", PASSWORD),
        ("gone@koha.nz", PASSWORD),
    ],
    ids=["wrong-password", "unknown-email", "deactivated"],
)
def test_every_failure_gives_the_same_message(client, email, password):
    """The response never says which part of the login was wrong."""
    response = log_in(client, email, password)
    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS_MESSAGE


def test_empty_fields_are_rejected(client):
    """The server also refuses empty fields."""
    assert log_in(client, "", "").status_code == 422


def test_me_requires_a_valid_token(client):
    """No token and a garbage token both give 401."""
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth_header("garbage")).status_code == 401


def test_me_returns_the_logged_in_user(client):
    """A valid token returns that user."""
    token = log_in(client, "driver@koha.nz").json()["access_token"]
    response = client.get("/api/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["email"] == "driver@koha.nz"


def test_expired_token_is_refused(client):
    """An expired token gives 401, which sends the user to the login page."""
    token = create_access_token(1, "admin", timedelta(seconds=-5))
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401


def test_driver_gets_403_on_an_admin_endpoint(client):
    """Role check on the server: a driver cannot use an Admin endpoint."""
    token = log_in(client, "driver@koha.nz").json()["access_token"]
    assert client.get("/admin-only", headers=auth_header(token)).status_code == 403


def test_admin_can_use_an_admin_endpoint(client):
    """The Admin passes the same guard."""
    token = log_in(client, "admin@koha.nz").json()["access_token"]
    assert client.get("/admin-only", headers=auth_header(token)).status_code == 200


def test_token_stops_working_when_the_account_is_deactivated(client, session_factory):
    """The user is reloaded on every request, so deactivation takes effect at once."""
    token = log_in(client, "driver@koha.nz").json()["access_token"]
    with session_factory() as db:
        db.query(User).filter_by(email="driver@koha.nz").update({"is_active": False})
        db.commit()
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401


def test_sixth_attempt_is_blocked_even_with_the_right_password(client):
    """After 5 failures the next attempt gets 429 with a Retry-After header."""
    for _ in range(5):
        assert log_in(client, "admin@koha.nz", "wrong").status_code == 401
    blocked = log_in(client, "admin@koha.nz")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def test_a_successful_login_resets_the_failure_count(client):
    """Four failures, a success, then four more failures do not trigger the block."""
    for _ in range(4):
        log_in(client, "admin@koha.nz", "wrong")
    assert log_in(client, "admin@koha.nz").status_code == 200
    for _ in range(4):
        assert log_in(client, "admin@koha.nz", "wrong").status_code == 401
