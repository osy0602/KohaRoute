"""Password hashing.

Only hashing lives here for now (the seed script needs it). Part 2 adds password checking and
login tokens to this same module.
"""

import bcrypt

# bcrypt's cost factor: each +1 doubles the work. 12 is slow enough (about a quarter of a
# second) to make guessing passwords expensive. Tests lower it so they stay fast.
BCRYPT_ROUNDS = 12

# bcrypt only reads the first 72 bytes of a password. Refusing longer ones is safer than
# silently ignoring the rest.
MAX_PASSWORD_BYTES = 72


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
