"""FastAPI application factory.

Run from the backend folder with: ``uvicorn app.main:app --reload``.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.config import get_config


def create_app() -> FastAPI:
    """Build the FastAPI application and attach middleware and routers.

    A factory (rather than module-level setup) keeps start-up steps in one place and lets
    later parts add routers in a single, readable list.

    Returns:
        The configured application.
    """
    config = get_config()
    application = FastAPI(title="KohaRoute API", version=__version__)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    return application


app = create_app()
