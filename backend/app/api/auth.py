"""Auth endpoints: POST /api/auth/login and GET /api/auth/me (US-01)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, role_name
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut
from app.security import create_access_token
from app.services.auth_service import (
    INVALID_CREDENTIALS_MESSAGE,
    authenticate_user,
    normalise_email,
)
from app.services.login_throttle import LoginThrottle
from app.services.session_policy import get_session_minutes

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60

router = APIRouter(prefix="/api/auth", tags=["auth"])

# One throttle for the whole process; tests replace it through get_login_throttle.
_login_throttle = LoginThrottle(LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS)


def get_login_throttle() -> LoginThrottle:
    """Dependency that returns the shared login throttle."""
    return _login_throttle


def current_session_minutes(db: Session = Depends(get_db)) -> int:
    """Dependency that returns the session length from settings."""
    return get_session_minutes(db)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    throttle: LoginThrottle = Depends(get_login_throttle),
    session_minutes: int = Depends(current_session_minutes),
) -> LoginResponse:
    """Log in with email and password. Admin and drivers use the same endpoint."""
    throttle_key = normalise_email(payload.email)

    if throttle.is_blocked(throttle_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(throttle.retry_after_seconds(throttle_key))},
        )

    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        throttle.record_failure(throttle_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS_MESSAGE,
        )

    throttle.reset(throttle_key)
    token = create_access_token(user.id, role_name(user), timedelta(minutes=session_minutes))
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)) -> User:
    """Return the logged-in user (the frontend uses this to restore a session)."""
    return user
