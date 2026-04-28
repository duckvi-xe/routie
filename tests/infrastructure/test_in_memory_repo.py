"""Tests for infrastructure layer — in-memory repositories."""

from uuid import UUID

import pytest

from routie.domain.enums import ActivityType
from routie.domain.models import Route, UserProfile
from routie.infrastructure.in_memory_repo import (
    InMemoryRouteRepository,
    InMemoryUserProfileRepository,
)


@pytest.fixture
def profile_repo() -> InMemoryUserProfileRepository:
    return InMemoryUserProfileRepository()


@pytest.fixture
def route_repo() -> InMemoryRouteRepository:
    return InMemoryRouteRepository()


@pytest.mark.asyncio
class TestInMemoryUserProfileRepository:
    async def test_save_and_get(self, profile_repo: InMemoryUserProfileRepository):
        profile = UserProfile.new(name="Test", activity_type=ActivityType.RUNNING)
        await profile_repo.save(profile)
        fetched = await profile_repo.get_by_id(profile.id)
        assert fetched is not None
        assert fetched.id == profile.id
        assert fetched.name == "Test"

    async def test_get_nonexistent_returns_none(
        self, profile_repo: InMemoryUserProfileRepository
    ):
        result = await profile_repo.get_by_id(
            UUID("00000000-0000-0000-0000-000000000000")
        )
        assert result is None

    async def test_delete(self, profile_repo: InMemoryUserProfileRepository):
        profile = UserProfile.new(name="DeleteMe", activity_type=ActivityType.RUNNING)
        await profile_repo.save(profile)
        await profile_repo.delete(profile.id)
        assert await profile_repo.get_by_id(profile.id) is None

    async def test_delete_nonexistent_does_not_raise(
        self, profile_repo: InMemoryUserProfileRepository
    ):
        # Should not raise for deleting a missing profile
        await profile_repo.delete(
            UUID("00000000-0000-0000-0000-000000000000")
        )

    async def test_update_overwrites(self, profile_repo: InMemoryUserProfileRepository):
        profile = UserProfile.new(name="Original", activity_type=ActivityType.RUNNING)
        await profile_repo.save(profile)
        updated = UserProfile(
            id=profile.id,
            name="Updated",
            activity_type=profile.activity_type,
            skill_level=profile.skill_level,
            avg_speed_kmh=profile.avg_speed_kmh,
            max_distance_km=profile.max_distance_km,
            preferred_terrain=profile.preferred_terrain,
            preferred_direction=profile.preferred_direction,
            home_coordinates=profile.home_coordinates,
            created_at=profile.created_at,
        )
        await profile_repo.save(updated)
        fetched = await profile_repo.get_by_id(profile.id)
        assert fetched is not None
        assert fetched.name == "Updated"


@pytest.mark.asyncio
class TestInMemoryRouteRepository:
    async def test_save_and_get(self, route_repo: InMemoryRouteRepository):
        route = Route.new(
            name="Test Route",
            activity_type=ActivityType.RUNNING,
            distance_km=10.0,
            elevation_gain_m=50.0,
            estimated_duration_min=60,
        )
        await route_repo.save(route)
        fetched = await route_repo.get_by_id(route.id)
        assert fetched is not None
        assert fetched.id == route.id

    async def test_get_nonexistent_returns_none(
        self, route_repo: InMemoryRouteRepository
    ):
        result = await route_repo.get_by_id(
            UUID("00000000-0000-0000-0000-000000000000")
        )
        assert result is None

    async def test_multiple_routes(self, route_repo: InMemoryRouteRepository):
        r1 = Route.new(
            name="Route A",
            activity_type=ActivityType.RUNNING,
            distance_km=5.0,
            elevation_gain_m=20.0,
            estimated_duration_min=30,
        )
        r2 = Route.new(
            name="Route B",
            activity_type=ActivityType.CYCLING,
            distance_km=50.0,
            elevation_gain_m=200.0,
            estimated_duration_min=120,
        )
        await route_repo.save(r1)
        await route_repo.save(r2)
        assert (await route_repo.get_by_id(r1.id)) is not None
        assert (await route_repo.get_by_id(r2.id)) is not None
