"""Deployment configuration read from environment variables.

Business rules (opening days, size presets, depot, ...) are deliberately NOT here. They live
in the database from Part 1, so they can change without redeploying. This module only holds
values that differ between machines: the database location and the allowed web origins.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'koharoute.db'}"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"


@dataclass(frozen=True)
class AppConfig:
    """Immutable bundle of deployment settings.

    Attributes:
        environment: Name of the running environment, e.g. "development".
        database_url: SQLAlchemy URL of the SQLite database.
        cors_origins: Web origins allowed to call the API from a browser.
    """

    environment: str
    database_url: str
    cors_origins: tuple[str, ...]


def _split_csv(raw_value: str) -> tuple[str, ...]:
    """Turn "a, b,,c" into ("a", "b", "c"), dropping blanks."""
    return tuple(item.strip() for item in raw_value.split(",") if item.strip())


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    """Read the configuration once and reuse it.

    Real environment variables win over values in backend/.env, so a server can override
    the file without editing it. The result is cached because the environment cannot change
    while the process runs; tests call ``get_config.cache_clear()`` when they change it.

    Returns:
        The application configuration.
    """
    load_dotenv(BACKEND_DIR / ".env")
    return AppConfig(
        environment=os.getenv("KOHA_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)),
    )
