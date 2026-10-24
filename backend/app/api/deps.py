"""Shared FastAPI dependencies: the current user and role guards (US-01)."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import TokenError, decode_access_token

# auto_error=False so a missing header gives our own 401 instead of FastAPI's 403.
_bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorised() -> HTTPException:
    """Build the 401 used for a missing, invalid or expired login."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not logged in or session expired",
        headers={"WWW-Authenticate": "Bearer"},
    )


def role_name(user: User) -> str:
    """Return the role as plain text, whether the column is a string or an Enum."""
    return getattr(user.role, "value", user.role)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Return the logged-in user.

    The user is reloaded from the database on every request, so a deactivated account
    stops working immediately.
    """
    if credentials is None:
        raise _unauthorised()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (TokenError, KeyError, ValueError):
        raise _unauthorised()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorised()
    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """Build a dependency that returns 403 unless the user has one of the roles."""

    def check_role(user: User = Depends(get_current_user)) -> User:
        if role_name(user) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource",
            )
        return user

    return check_role


# Ready-made guards. From Part 5 on, every Admin router is created with
# ``APIRouter(dependencies=[Depends(require_admin)])`` so no endpoint can be missed.
require_admin = require_role("admin")
require_driver = require_role("driver")
