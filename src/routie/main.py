"""Routie — FastAPI application entry point.

Usage:
    uvicorn routie.main:app --reload

To use SQL persistence instead of in-memory:
    USE_DB=true uvicorn routie.main:app --reload
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from routie.config import Settings
from routie.infrastructure.database import (
    create_all_tables,
    create_engine,
    session_factory,
)
from routie.infrastructure.in_memory_repo import (
    InMemoryRouteRepository,
    InMemoryUserProfileRepository,
)
from routie.infrastructure.repository import (
    SqlRouteRepository,
    SqlUserProfileRepository,
)
from routie.service.providers.mock import MockRouteProvider
from routie.use_cases.manage_profile import ManageProfileUseCase
from routie.use_cases.plan_route import PlanRouteUseCase
from routie.web.api import create_router

# Path to the built Svelte frontend (frontend/dist/)
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# Module-level holders for SQL engine + session maker (used by startup)
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def _ensure_static_dir() -> Path:
    """Ensure static dir exists, falling back to a generated placeholder if not built."""
    if _STATIC_DIR.exists():
        return _STATIC_DIR
    fallback = Path(__file__).parent / "web" / "static"
    fallback.mkdir(parents=True, exist_ok=True)
    _write_placeholder_index(fallback)
    return fallback


def _write_placeholder_index(static_dir: Path) -> None:
    """Write a minimal placeholder when the Svelte frontend hasn't been built."""
    index = static_dir / "index.html"
    if not index.exists():
        index.write_text(
            "<!DOCTYPE html><html><body>"
            "<h1>Routie Frontend</h1>"
            "<p>Build the frontend first: <code>cd frontend && npm run build</code></p>"
            "</body></html>"
        )


def create_app() -> FastAPI:
    """Build the FastAPI application with dependency injection."""
    global _engine, _session_maker

    settings = Settings()

    # Infrastructure
    if settings.use_database:
        _engine = create_engine(settings.database_url)
        _session_maker = session_factory(_engine)
        profile_repo = SqlUserProfileRepository(_session_maker)
        route_repo = SqlRouteRepository(_session_maker)
    else:
        profile_repo = InMemoryUserProfileRepository()
        route_repo = InMemoryRouteRepository()

    route_provider = MockRouteProvider()

    # Use cases
    manage_profile_uc = ManageProfileUseCase(profile_repo=profile_repo)
    plan_route_uc = PlanRouteUseCase(
        profile_repo=profile_repo,
        route_repo=route_repo,
        route_provider=route_provider,
    )

    # Web
    router = create_router(
        manage_profile_uc=manage_profile_uc,
        plan_route_uc=plan_route_uc,
    )

    app = FastAPI(
        title="Routie API",
        description="Route planning for runners and cyclists",
        version="0.1.0",
    )
    app.include_router(router, prefix="/api/v1")

    # Startup: create tables if using SQL database
    if settings.use_database:

        @app.on_event("startup")
        async def _init_db() -> None:
            assert _engine is not None
            await create_all_tables(_engine)

    # Mount static frontend files — catches all non-API paths
    static_dir = _ensure_static_dir()
    app.mount(
        "/",
        StaticFiles(directory=str(static_dir), html=True),
        name="frontend",
    )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = Settings()
    uvicorn.run(
        "routie.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=True,
    )
