import pytest

from app.config import DEFAULT_DATABASE_URL, get_config


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    """Ignore any real backend/.env and start each test with a fresh cache."""
    monkeypatch.setattr("app.config.load_dotenv", lambda *args, **kwargs: None)
    for name in ("KOHA_ENV", "DATABASE_URL", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    get_config.cache_clear()
    yield
    get_config.cache_clear()


def test_defaults_are_used_when_nothing_is_set():
    config = get_config()
    assert config.environment == "development"
    assert config.database_url == DEFAULT_DATABASE_URL
    assert config.cors_origins == ("http://localhost:5173",)


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("KOHA_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.example, http://b.example,,")
    config = get_config()
    assert config.environment == "test"
    assert config.database_url == "sqlite://"
    assert config.cors_origins == ("http://a.example", "http://b.example")


def test_config_is_cached():
    assert get_config() is get_config()
