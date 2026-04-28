"""Tests for the SQLAlchemy-backed repositories.

These tests use an in-memory SQLite database so they're fast and isolated.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from routie.domain.enums import (
    ActivityType,
    DifficultyLevel,
    Direction,
    SkillLevel,
    TerrainType,
)
from routie.domain.models import Route, UserProfile
from routie.domain.value_objects import Coordinates
from routie.infrastructure.database import (
    create_all_tables,
    create_engine,
    drop_all_tables,
    session_factory,
)
from routie.infrastructure.orm import RouteModel, UserProfileModel
from routie.infrastructure.repository import (
    SqlRouteRepository,
    SqlUserProfileRepository,
)

SESSION_MAKER: async_sessionmaker[AsyncSession] | None = None


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def _setup_db():
    """Create a fresh in-memory SQLite database per test module."""
    # Use shared-cache so multiple async sessions see the same in-memory DB
    engine = create_engine("sqlite+aiosqlite:///file::memory:?cache=shared")
    global SESSION_MAKER
    SESSION_MAKER = session_factory(engine)
    await create_all_tables(engine)
    yield
    await drop_all_tables(engine)
    await engine.dispose()


@pytest.fixture
async def profile_repo():
    assert SESSION_MAKER is not None
    repo = SqlUserProfileRepository(SESSION_MAKER)
    # Clean slate before each test
    async with SESSION_MAKER() as session:
        result = await session.execute(select(UserProfileModel))
        for model in result.scalars().all():
            await session.delete(model)
        await session.commit()
    return repo


@pytest.fixture
async def route_repo():
    assert SESSION_MAKER is not None
    repo = SqlRouteRepository(SESSION_MAKER)
    async with SESSION_MAKER() as session:
        result = await session.execute(select(RouteModel))
        for model in result.scalars().all():
            await session.delete(model)
        await session.commit()
    return repo


# ---------------------------------------------------------------------------
#  Test fixtures for test data
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_profile() -> UserProfile:
    return UserProfile.new(
        name="Andrea",
        activity_type=ActivityType.RUNNING,
        skill_level=SkillLevel.INTERMEDIATE,
        max_distance_km=21.0,
        preferred_terrain=TerrainType.MIXED,
        preferred_direction=Direction.NE,
        home_coordinates=Coordinates(latitude=45.4642, longitude=9.1900),
    )


@pytest.fixture
def sample_route() -> Route:
    return Route.new(
        name="Morning Run Mixed 10km",
        activity_type=ActivityType.RUNNING,
        distance_km=10.0,
        elevation_gain_m=150.0,
        estimated_duration_min=50,
        waypoints=[
            Coordinates(latitude=45.4642, longitude=9.1900),
            Coordinates(latitude=45.4742, longitude=9.2000),
            Coordinates(latitude=45.4842, longitude=9.2100),
        ],
    )


# ---------------------------------------------------------------------------
#  SqlUserProfileRepository tests
# ---------------------------------------------------------------------------


class TestSqlUserProfileRepository:
    async def test_save_and_get(self, profile_repo, sample_profile):
        await profile_repo.save(sample_profile)
        fetched = await profile_repo.get_by_id(sample_profile.id)
        assert fetched is not None
        assert fetched.id == sample_profile.id
        assert fetched.name == "Andrea"
        assert fetched.activity_type == ActivityType.RUNNING
        assert fetched.skill_level == SkillLevel.INTERMEDIATE
        assert fetched.max_distance_km == 21.0
        assert fetched.preferred_terrain == TerrainType.MIXED
        assert fetched.preferred_direction == Direction.NE
        assert fetched.home_coordinates is not None
        assert fetched.home_coordinates.latitude == 45.4642

    async def test_get_nonexistent_returns_none(self, profile_repo):
        result = await profile_repo.get_by_id(
            UUID("00000000-0000-0000-0000-000000000000")
        )
        assert result is None

    async def test_update_overwrites(self, profile_repo, sample_profile):
        await profile_repo.save(sample_profile)
        updated = sample_profile.with_speed(15.0)
        await profile_repo.save(updated)

        fetched = await profile_repo.get_by_id(sample_profile.id)
        assert fetched is not None
        assert fetched.avg_speed_kmh == 15.0

    async def test_delete(self, profile_repo, sample_profile):
        await profile_repo.save(sample_profile)
        await profile_repo.delete(sample_profile.id)
        fetched = await profile_repo.get_by_id(sample_profile.id)
        assert fetched is None

    async def test_delete_nonexistent_does_not_raise(self, profile_repo):
        # Should not raise for deleting a missing profile
        await profile_repo.delete(
            UUID("00000000-0000-0000-0000-000000000000")
        )

    async def test_multiple_profiles(self, profile_repo, sample_profile):
        await profile_repo.save(sample_profile)
        profile2 = UserProfile.new(
            name="Marco",
            activity_type=ActivityType.CYCLING,
            skill_level=SkillLevel.ADVANCED,
        )
        await profile_repo.save(profile2)

        fetched1 = await profile_repo.get_by_id(sample_profile.id)
        fetched2 = await profile_repo.get_by_id(profile2.id)
        assert fetched1 is not None
        assert fetched2 is not None
        assert fetched1.name == "Andrea"
        assert fetched2.name == "Marco"

    async def test_profile_without_home_coordinates(
        self, profile_repo
    ):
        profile_no_home = UserProfile.new(
            name="NoHome", activity_type=ActivityType.RUNNING
        )
        await profile_repo.save(profile_no_home)
        fetched = await profile_repo.get_by_id(profile_no_home.id)
        assert fetched is not None
        assert fetched.home_coordinates is None

    async def test_preserves_created_at(self, profile_repo, sample_profile):
        await profile_repo.save(sample_profile)
        fetched = await profile_repo.get_by_id(sample_profile.id)
        assert fetched is not None
        assert fetched.created_at == sample_profile.created_at


# ---------------------------------------------------------------------------
#  SqlRouteRepository tests
# ---------------------------------------------------------------------------


class TestSqlRouteRepository:
    async def test_save_and_get_route(self, route_repo, sample_route):
        await route_repo.save(sample_route)
        fetched = await route_repo.get_by_id(sample_route.id)
        assert fetched is not None
        assert fetched.id == sample_route.id
        assert fetched.name == "Morning Run Mixed 10km"
        assert fetched.distance_km == 10.0
        assert fetched.elevation_gain_m == 150.0
        assert fetched.estimated_duration_min == 50
        # 10km + 150m/50 = 13 points → MODERATE (threshold 12)
        assert fetched.difficulty == DifficultyLevel.MODERATE

    async def test_get_nonexistent_route_returns_none(self, route_repo):
        result = await route_repo.get_by_id(
            UUID("00000000-0000-0000-0000-000000000000")
        )
        assert result is None

    async def test_route_without_waypoints(self, route_repo):
        route = Route.new(
            name="No Waypoints",
            activity_type=ActivityType.RUNNING,
            distance_km=5.0,
            elevation_gain_m=20.0,
            estimated_duration_min=30,
        )
        await route_repo.save(route)
        fetched = await route_repo.get_by_id(route.id)
        assert fetched is not None
        assert fetched.waypoints == []

    async def test_route_waypoints_roundtrip(self, route_repo, sample_route):
        await route_repo.save(sample_route)
        fetched = await route_repo.get_by_id(sample_route.id)
        assert fetched is not None
        assert len(fetched.waypoints) == 3
        assert fetched.waypoints[0].latitude == 45.4642
        assert fetched.waypoints[0].longitude == 9.1900
        assert fetched.waypoints[2].latitude == 45.4842

    async def test_multiple_routes(self, route_repo, sample_route):
        await route_repo.save(sample_route)
        route2 = Route.new(
            name="Evening Ride",
            activity_type=ActivityType.CYCLING,
            distance_km=30.0,
            elevation_gain_m=200.0,
            estimated_duration_min=90,
        )
        await route_repo.save(route2)

        fetched1 = await route_repo.get_by_id(sample_route.id)
        fetched2 = await route_repo.get_by_id(route2.id)
        assert fetched1 is not None
        assert fetched2 is not None
        assert fetched1.activity_type == ActivityType.RUNNING
        assert fetched2.activity_type == ActivityType.CYCLING

    async def test_preserves_created_at(self, route_repo, sample_route):
        await route_repo.save(sample_route)
        fetched = await route_repo.get_by_id(sample_route.id)
        assert fetched is not None
        assert fetched.created_at == sample_route.created_at

    async def test_difficulty_calculation_preserved(self, route_repo):
        hard_route = Route.new(
            name="Hard Trail",
            activity_type=ActivityType.RUNNING,
            distance_km=30.0,
            elevation_gain_m=800.0,
            estimated_duration_min=180,
        )
        await route_repo.save(hard_route)
        fetched = await route_repo.get_by_id(hard_route.id)
        assert fetched is not None
        assert fetched.difficulty == DifficultyLevel.HARD
