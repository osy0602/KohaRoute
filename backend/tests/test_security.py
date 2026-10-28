import bcrypt
import pytest

from app.security import MAX_PASSWORD_BYTES, hash_password


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    """Use the cheapest bcrypt setting so the tests run quickly."""
    monkeypatch.setattr("app.security.BCRYPT_ROUNDS", 4)


def test_hash_is_bcrypt_and_matches_the_password():
    hashed = hash_password("a-good-password")
    assert hashed.startswith("$2")
    assert hashed != "a-good-password"
    assert bcrypt.checkpw(b"a-good-password", hashed.encode("ascii"))
    assert not bcrypt.checkpw(b"a-wrong-password", hashed.encode("ascii"))


def test_same_password_gets_a_different_hash_each_time():
    assert hash_password("same-password") != hash_password("same-password")


def test_password_longer_than_72_bytes_is_refused():
    with pytest.raises(ValueError, match="at most"):
        hash_password("x" * (MAX_PASSWORD_BYTES + 1))


def test_password_of_exactly_72_bytes_is_accepted():
    assert hash_password("x" * MAX_PASSWORD_BYTES).startswith("$2")
