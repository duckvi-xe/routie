"""Tests for the web API layer (FastAPI)."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from routie.infrastructure.in_memory_repo import (
    InMemoryRouteRepository,
    InMemoryUserProfileRepository,
)
from routie.service.providers.mock import MockRouteProvider
from routie.use_cases.manage_profile import ManageProfileUseCase
from routie.use_cases.plan_route import PlanRouteUseCase
from routie.web.api import create_router


@pytest.fixture
def app() -> FastAPI:
    """Build a FastAPI app wired with in-memory dependencies."""
    profile_repo = InMemoryUserProfileRepository()
    route_repo = InMemoryRouteRepository()
    route_provider = MockRouteProvider()

    manage_uc = ManageProfileUseCase(profile_repo=profile_repo)
    plan_uc = PlanRouteUseCase(
        profile_repo=profile_repo,
        route_repo=route_repo,
        route_provider=route_provider,
    )

    router = create_router(manage_profile_uc=manage_uc, plan_route_uc=plan_uc)
    application = FastAPI(title="Routie API", version="0.1.0")
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
#  Health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


# ---------------------------------------------------------------------------
#  Profiles
# ---------------------------------------------------------------------------


class TestCreateProfile:
    async def test_create_profile(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/profiles",
            json={
                "name": "Andrea",
                "activity_type": "running",
                "skill_level": "intermediate",
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["name"] == "Andrea"
        assert data["activity_type"] == "running"
        assert data["skill_level"] == "intermediate"
        assert "id" in data
        assert UUID(data["id"])

    async def test_create_profile_invalid_activity_type(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/profiles",
            json={"name": "Test", "activity_type": "swimming"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_create_profile_missing_name(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/profiles",
            json={"activity_type": "running"},
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetProfile:
    async def test_get_existing_profile(self, client: AsyncClient):
        created = await client.post(
            "/api/v1/profiles",
            json={"name": "Anna", "activity_type": "running"},
        )
        profile_id = created.json()["id"]

        resp = await client.get(f"/api/v1/profiles/{profile_id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["name"] == "Anna"

    async def test_get_nonexistent_profile(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/profiles/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_profile_invalid_uuid(self, client: AsyncClient):
        resp = await client.get("/api/v1/profiles/not-a-uuid")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateProfile:
    async def test_update_profile_name(self, client: AsyncClient):
        created = await client.post(
            "/api/v1/profiles",
            json={"name": "Before", "activity_type": "running"},
        )
        profile_id = created.json()["id"]

        resp = await client.patch(
            f"/api/v1/profiles/{profile_id}",
            json={"name": "After"},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["name"] == "After"


class TestDeleteProfile:
    async def test_delete_profile(self, client: AsyncClient):
        created = await client.post(
            "/api/v1/profiles",
            json={"name": "ToDelete", "activity_type": "running"},
        )
        profile_id = created.json()["id"]

        resp = await client.delete(f"/api/v1/profiles/{profile_id}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # Confirm it's gone
        get_resp = await client.get(f"/api/v1/profiles/{profile_id}")
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
#  Routes
# ---------------------------------------------------------------------------


class TestPlanRoute:
    async def test_plan_route(self, client: AsyncClient):
        # Create a profile first
        profile_resp = await client.post(
            "/api/v1/profiles",
            json={
                "name": "Runner",
                "activity_type": "running",
                "skill_level": "intermediate",
            },
        )
        profile_id = profile_resp.json()["id"]

        # Plan a route
        resp = await client.post(
            "/api/v1/routes/plan",
            json={
                "profile_id": profile_id,
                "activity_type": "running",
                "max_distance_km": 10.0,
            },
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["activity_type"] == "running"
        assert data["distance_km"] <= 10.0
        assert "id" in data
        assert "name" in data

    async def test_plan_route_nonexistent_profile(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/routes/plan",
            json={
                "profile_id": "00000000-0000-0000-0000-000000000000",
                "activity_type": "running",
            },
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "PROFILE_NOT_FOUND" in resp.text


class TestGetRoute:
    async def test_get_route(self, client: AsyncClient):
        # Create profile and plan route
        profile_resp = await client.post(
            "/api/v1/profiles",
            json={"name": "Runner", "activity_type": "running"},
        )
        profile_id = profile_resp.json()["id"]

        plan_resp = await client.post(
            "/api/v1/routes/plan",
            json={
                "profile_id": profile_id,
                "activity_type": "running",
            },
        )
        route_id = plan_resp.json()["id"]

        resp = await client.get(f"/api/v1/routes/{route_id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["id"] == route_id

    async def test_get_nonexistent_route(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/routes/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
