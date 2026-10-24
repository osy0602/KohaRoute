"""Deployment configuration read from environment variables.

Business rules (opening days, size presets, depot, ...) are deliberately NOT here. They live
in the database from Part 1, so they can change without redeploying. This module only holds
values that differ between machines: the database location and the allowed web origins.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'koharoute.db'}"
DEFAULT_CORS_ORIGINS = "http://localhost:5173"
# Demo-only defaults so a fresh checkout can be seeded and logged into straight away.
DEFAULT_SEED_ADMIN_PASSWORD = "Koha-Admin-2026!"
DEFAULT_SEED_DRIVER_PASSWORD = "Koha-Driver-2026!"


@dataclass(frozen=True)
class AppConfig:
    """Immutable bundle of deployment settings.

    Attributes:
        environment: Name of the running environment, e.g. "development".
        database_url: SQLAlchemy URL of the SQLite database.
        cors_origins: Web origins allowed to call the API from a browser.
        seed_admin_password: Password the seed script gives the demo Admin (demo use only).
        seed_driver_password: Password the seed script gives the demo drivers (demo use only).
        ors_api_key: Optional OpenRouteService key; omitted from the config repr.
        photo_storage_dir: Directory for private, randomly named uploaded photographs.
    """

    environment: str
    database_url: str
    cors_origins: tuple[str, ...]
    seed_admin_password: str = DEFAULT_SEED_ADMIN_PASSWORD
    seed_driver_password: str = DEFAULT_SEED_DRIVER_PASSWORD
    ors_api_key: str = field(default="", repr=False)
    photo_storage_dir: Path = BACKEND_DIR / "uploads" / "photos"


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
        seed_admin_password=os.getenv("SEED_ADMIN_PASSWORD", DEFAULT_SEED_ADMIN_PASSWORD),
        seed_driver_password=os.getenv("SEED_DRIVER_PASSWORD", DEFAULT_SEED_DRIVER_PASSWORD),
        ors_api_key=os.getenv("ORS_API_KEY", ""),
        photo_storage_dir=Path(
            os.getenv("PHOTO_STORAGE_DIR", str(BACKEND_DIR / "uploads" / "photos"))
        ),
    )
