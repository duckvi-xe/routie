"""Routie — FastAPI application entry point.

Usage:
    uvicorn routie.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from routie.config import Settings
from routie.infrastructure.in_memory_repo import (
    InMemoryRouteRepository,
    InMemoryUserProfileRepository,
)
from routie.service.providers.mock import MockRouteProvider
from routie.use_cases.manage_profile import ManageProfileUseCase
from routie.use_cases.plan_route import PlanRouteUseCase
from routie.web.api import create_router


def create_app() -> FastAPI:
    """Build the FastAPI application with dependency injection."""
    # Infrastructure
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
