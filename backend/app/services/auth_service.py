"""Login rules (US-01): find the user and check the password."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.security import dummy_password_hash, verify_password

# One message for every failure, so the response never says which part was wrong.
INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"


def normalise_email(email: str) -> str:
    """Return the email trimmed and lower-cased (emails are not case sensitive)."""
    return email.strip().lower()


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the active user for these credentials, or None.

    A password check always runs (against a dummy hash for unknown emails) so timing
    does not reveal whether the email exists. A deactivated account fails exactly like
    a wrong password.
    """
    user = db.scalars(select(User).where(func.lower(User.email) == normalise_email(email))).first()
    hash_to_check = user.password_hash if user else dummy_password_hash()
    password_ok = verify_password(password, hash_to_check)
    if user is None or not password_ok or not user.is_active:
        return None
    return user
