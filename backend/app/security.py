"""Password hashing and signed access tokens for staff authentication."""

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import bcrypt
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

_environment = os.getenv("KOHA_ENV", "development").lower()
_configured_secret = os.getenv("JWT_SECRET_KEY")
if not _configured_secret and _environment not in {"development", "test"}:
    raise RuntimeError("JWT_SECRET_KEY must be set outside development and test environments")
JWT_SECRET_KEY = _configured_secret or "koha-route-development-only-secret"

# bcrypt's cost factor: each +1 doubles the work. 12 is slow enough (about a quarter of a
# second) to make guessing passwords expensive. Tests lower it so they stay fast.
BCRYPT_ROUNDS = 12

# bcrypt only reads the first 72 bytes of a password. Refusing longer ones is safer than
# silently ignoring the rest.
MAX_PASSWORD_BYTES = 72


class TokenError(ValueError):
    """Raised when an access token is malformed, invalid, or expired."""


def hash_password(plain_password: str) -> str:
    """Hash a password with bcrypt and a fresh random salt.

    Args:
        plain_password: The password as typed. It is never stored.

    Returns:
        The bcrypt hash as text, safe to store in the ``users`` table.

    Raises:
        ValueError: If the password is longer than 72 bytes once encoded as UTF-8.
    """
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Return whether a plaintext password matches a stored bcrypt hash."""
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, stored_hash.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


@lru_cache(maxsize=1)
def dummy_password_hash() -> str:
    """Return a cached bcrypt hash for constant-work checks of unknown email addresses."""
    return hash_password("koha-route-dummy-password")


def _base64url_encode(value: bytes) -> str:
    """Encode bytes using unpadded URL-safe Base64."""
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    """Decode unpadded URL-safe Base64."""
    padded = value + "=" * (-len(value) % 4)
    return base64.b64decode(padded, altchars=b"-_", validate=True)


def create_access_token(user_id: int, role: str, lifetime: timedelta) -> str:
    """Create an HS256 JWT with a user id, role, issue time, and expiry."""
    issued_at = int(time.time())
    header_json = json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":"))
    header = _base64url_encode(header_json.encode())
    payload = _base64url_encode(
        json.dumps(
            {
                "sub": str(user_id),
                "role": role,
                "iat": issued_at,
                "exp": issued_at + int(lifetime.total_seconds()),
            },
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, int | str]:
    """Verify an HS256 JWT and return its claims, rejecting malformed or expired tokens."""
    try:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_base64url_decode(header_part))
        if not isinstance(header, dict):
            raise TokenError("Invalid token header")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_signature = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        supplied_signature = _base64url_decode(signature_part)
        valid_algorithm = header.get("alg") == "HS256"
        valid_signature = hmac.compare_digest(expected_signature, supplied_signature)
        if not valid_algorithm or not valid_signature:
            raise TokenError("Invalid token signature")

        payload = json.loads(_base64url_decode(payload_part))
        if not isinstance(payload, dict) or type(payload.get("exp")) is not int:
            raise TokenError("Invalid token claims")
        if payload["exp"] <= int(time.time()):
            raise TokenError("Token has expired")
        if not isinstance(payload.get("sub"), str) or not isinstance(payload.get("role"), str):
            raise TokenError("Invalid token claims")
        return payload
    except TokenError:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ) as error:
        raise TokenError("Invalid token") from error
