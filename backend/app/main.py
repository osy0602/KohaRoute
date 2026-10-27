"""FastAPI application factory.

Run from the backend folder with: ``uvicorn app.main:app --reload``.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.admin_bookings import router as admin_bookings_router
from app.api.admin_vehicles import router as admin_vehicles_router
from app.api.auth import router as auth_router
from app.api.bookings import router as bookings_router
from app.api.health import router as health_router
from app.config import get_config
from app.services.geocoding_service import (
    AddressRateLimiter,
    AddressSearchService,
    OrsAddressProvider,
)


def create_app() -> FastAPI:
    """Build the FastAPI application and attach middleware and routers.

    A factory (rather than module-level setup) keeps start-up steps in one place and lets
    later parts add routers in a single, readable list.

    Returns:
        The configured application.
    """
    config = get_config()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """Share one async HTTP connection pool for ORS lookups per app process."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0)) as client:
            application.state.address_search = AddressSearchService(
                OrsAddressProvider(client, config.ors_api_key)
            )
            application.state.address_rate_limiter = AddressRateLimiter()
            yield

    application = FastAPI(title="KohaRoute API", version=__version__, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(bookings_router)
    application.include_router(admin_bookings_router)
    application.include_router(admin_vehicles_router)
    return application


app = create_app()
