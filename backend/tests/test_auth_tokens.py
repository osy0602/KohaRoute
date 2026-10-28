"""Unit tests for password checking and login tokens (US-01)."""

from datetime import timedelta

import pytest

from app.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

PLAIN = "correct horse battery staple"


@pytest.fixture(scope="module")
def stored_hash() -> str:
    """Hash once per module: bcrypt is deliberately slow."""
    return hash_password(PLAIN)


def test_hash_is_not_the_plain_password(stored_hash):
    """The stored value never contains the password."""
    assert PLAIN not in stored_hash
    assert stored_hash.startswith("$2")


def test_verify_accepts_the_right_password_only(stored_hash):
    """Only the original password matches the hash."""
    assert verify_password(PLAIN, stored_hash) is True
    assert verify_password("wrong", stored_hash) is False


def test_verify_treats_a_malformed_hash_as_a_mismatch():
    """A broken hash fails safely instead of raising."""
    assert verify_password(PLAIN, "not-a-bcrypt-hash") is False


def test_verify_treats_an_overlong_password_as_a_mismatch(stored_hash):
    """A password over bcrypt's 72-byte limit is a mismatch, not an error."""
    assert verify_password("x" * 100, stored_hash) is False


def test_token_round_trip_keeps_user_and_role():
    """A fresh token decodes back to the same user id and role."""
    payload = decode_access_token(create_access_token(7, "driver", timedelta(minutes=5)))
    assert payload["sub"] == "7"
    assert payload["role"] == "driver"


def test_token_lifetime_matches_the_requested_length():
    """The expiry is issue time plus the lifetime given (from settings)."""
    payload = decode_access_token(create_access_token(1, "admin", timedelta(minutes=30)))
    assert payload["exp"] - payload["iat"] == 30 * 60


def test_expired_token_is_rejected():
    """A token past its expiry raises TokenError."""
    token = create_access_token(1, "admin", timedelta(seconds=-5))
    with pytest.raises(TokenError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    """Changing the signature invalidates the token."""
    token = create_access_token(1, "admin", timedelta(minutes=5))
    with pytest.raises(TokenError):
        decode_access_token(token[:-2] + "xx")
