"""Tests for use cases — plan_route and manage_profile."""

from __future__ import annotations

from uuid import UUID

import pytest

from routie.domain.enums import (
    ActivityType,
    Direction,
    SkillLevel,
    TerrainType,
)
from routie.domain.models import Route, RoutePlanRequest, UserProfile
from routie.domain.value_objects import Coordinates
from routie.use_cases.manage_profile import (
    CreateProfileRequest,
    ManageProfileUseCase,
    ProfileNotFoundError,
    UpdateProfileRequest,
)
from routie.use_cases.plan_route import PlanRouteRequest, PlanRouteUseCase

# ---------------------------------------------------------------------------
#  Fake repositories (in-memory, no I/O, test doubles)
# ---------------------------------------------------------------------------


class FakeUserProfileRepository:
    """In-memory repository for testing."""

    def __init__(self) -> None:
        self._profiles: dict[UUID, UserProfile] = {}

    async def save(self, profile: UserProfile) -> None:
        self._profiles[profile.id] = profile

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        return self._profiles.get(profile_id)

    async def delete(self, profile_id: UUID) -> None:
        self._profiles.pop(profile_id, None)


class FakeRouteRepository:
    """In-memory route repository for testing."""

    def __init__(self) -> None:
        self._routes: dict[UUID, Route] = {}

    async def save(self, route: Route) -> None:
        self._routes[route.id] = route

    async def get_by_id(self, route_id: UUID) -> Route | None:
        return self._routes.get(route_id)


class FakeRouteProvider:
    """A deterministic fake provider for testing.

    Returns a route that exactly matches the request parameters,
    so tests can assert on constraints.
    """

    def __init__(self) -> None:
        self.last_request: RoutePlanRequest | None = None

    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: UserProfile,
    ) -> Route:
        distance = request.max_distance_km or 10.0
        duration = request.max_duration_min or 60
        elevation = distance * 5.0  # 5m per km
        return Route.new(
            name=f"Route for {profile.name}",
            activity_type=request.activity_type,
            distance_km=distance,
            elevation_gain_m=elevation,
            estimated_duration_min=duration,
            waypoints=[
                Coordinates(latitude=45.0, longitude=9.0),
                Coordinates(latitude=45.1, longitude=9.1),
            ],
        )


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def profile_repo() -> FakeUserProfileRepository:
    return FakeUserProfileRepository()


@pytest.fixture
def route_repo() -> FakeRouteRepository:
    return FakeRouteRepository()


@pytest.fixture
def route_provider() -> FakeRouteProvider:
    return FakeRouteProvider()


@pytest.fixture
def manage_profile_uc(profile_repo: FakeUserProfileRepository) -> ManageProfileUseCase:
    return ManageProfileUseCase(profile_repo=profile_repo)


@pytest.fixture
def plan_route_uc(
    profile_repo: FakeUserProfileRepository,
    route_repo: FakeRouteRepository,
    route_provider: FakeRouteProvider,
) -> PlanRouteUseCase:
    return PlanRouteUseCase(
        profile_repo=profile_repo,
        route_repo=route_repo,
        route_provider=route_provider,
    )


# ---------------------------------------------------------------------------
#  ManageProfileUseCase tests
# ---------------------------------------------------------------------------


class TestManageProfileUseCase:
    async def test_create_profile(self, manage_profile_uc: ManageProfileUseCase):
        profile = await manage_profile_uc.create(
            CreateProfileRequest(name="Andrea", activity_type=ActivityType.RUNNING)
        )
        assert profile.name == "Andrea"
        assert profile.activity_type == ActivityType.RUNNING
        assert profile.skill_level == SkillLevel.BEGINNER

    async def test_create_profile_with_full_details(
        self, manage_profile_uc: ManageProfileUseCase
    ):
        profile = await manage_profile_uc.create(
            CreateProfileRequest(
                name="Marco",
                activity_type=ActivityType.CYCLING,
                skill_level=SkillLevel.ADVANCED,
                avg_speed_kmh=28.0,
                max_distance_km=120.0,
                preferred_terrain=TerrainType.HILLY,
                preferred_direction=Direction.SW,
            )
        )
        assert profile.avg_speed_kmh == 28.0
        assert profile.max_distance_km == 120.0

    async def test_get_profile(self, manage_profile_uc: ManageProfileUseCase):
        created = await manage_profile_uc.create(
            CreateProfileRequest(name="Anna", activity_type=ActivityType.RUNNING)
        )
        fetched = await manage_profile_uc.get(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == "Anna"

    async def test_get_nonexistent_profile_raises_error(
        self, manage_profile_uc: ManageProfileUseCase
    ):
        with pytest.raises(ProfileNotFoundError):
            await manage_profile_uc.get(UUID("00000000-0000-0000-0000-000000000000"))

    async def test_update_profile(self, manage_profile_uc: ManageProfileUseCase):
        created = await manage_profile_uc.create(
            CreateProfileRequest(name="Test", activity_type=ActivityType.RUNNING)
        )
        updated = await manage_profile_uc.update(
            UpdateProfileRequest(profile_id=created.id, name="Updated")
        )
        assert updated.name == "Updated"
        assert updated.activity_type == ActivityType.RUNNING  # unchanged

    async def test_update_nonexistent_profile_raises_error(
        self, manage_profile_uc: ManageProfileUseCase
    ):
        with pytest.raises(ProfileNotFoundError):
            await manage_profile_uc.update(
                UpdateProfileRequest(
                    profile_id=UUID("00000000-0000-0000-0000-000000000000"),
                    name="Ghost",
                )
            )

    async def test_update_speed_only(self, manage_profile_uc: ManageProfileUseCase):
        created = await manage_profile_uc.create(
            CreateProfileRequest(name="Test", activity_type=ActivityType.RUNNING)
        )
        updated = await manage_profile_uc.update(
            UpdateProfileRequest(profile_id=created.id, avg_speed_kmh=6.0)
        )
        assert updated.avg_speed_kmh == 6.0
        assert updated.name == "Test"  # unchanged

    async def test_delete_profile(self, manage_profile_uc: ManageProfileUseCase):
        created = await manage_profile_uc.create(
            CreateProfileRequest(name="ToDelete", activity_type=ActivityType.RUNNING)
        )
        await manage_profile_uc.delete(created.id)
        with pytest.raises(ProfileNotFoundError):
            await manage_profile_uc.get(created.id)


# ---------------------------------------------------------------------------
#  PlanRouteUseCase tests
# ---------------------------------------------------------------------------


class TestPlanRouteUseCase:
    async def test_plan_route_basic(
        self,
        manage_profile_uc: ManageProfileUseCase,
        plan_route_uc: PlanRouteUseCase,
    ):
        profile = await manage_profile_uc.create(
            CreateProfileRequest(name="Runner", activity_type=ActivityType.RUNNING)
        )
        route = await plan_route_uc.execute(
            PlanRouteRequest(profile_id=profile.id, activity_type=ActivityType.RUNNING)
        )
        assert route.activity_type == ActivityType.RUNNING
        assert route.distance_km > 0
        assert route.estimated_duration_min > 0
        assert isinstance(route.id, UUID)

    async def test_plan_route_with_constraints(
        self,
        manage_profile_uc: ManageProfileUseCase,
        plan_route_uc: PlanRouteUseCase,
    ):
        profile = await manage_profile_uc.create(
            CreateProfileRequest(name="Cyclist", activity_type=ActivityType.CYCLING)
        )
        route = await plan_route_uc.execute(
            PlanRouteRequest(
                profile_id=profile.id,
                activity_type=ActivityType.CYCLING,
                max_distance_km=50.0,
                max_duration_min=120,
                preferred_direction=Direction.SE,
                terrain_type=TerrainType.FLAT,
            )
        )
        assert route.distance_km <= 50.0

    async def test_plan_route_with_nonexistent_profile_raises_error(
        self, plan_route_uc: PlanRouteUseCase
    ):
        with pytest.raises(ProfileNotFoundError):
            await plan_route_uc.execute(
                PlanRouteRequest(
                    profile_id=UUID(
                        "00000000-0000-0000-0000-000000000000"
                    ),
                    activity_type=ActivityType.RUNNING,
                )
            )

    async def test_planned_route_is_persisted(
        self,
        manage_profile_uc: ManageProfileUseCase,
        plan_route_uc: PlanRouteUseCase,
        route_repo: FakeRouteRepository,
    ):
        profile = await manage_profile_uc.create(
            CreateProfileRequest(name="Runner", activity_type=ActivityType.RUNNING)
        )
        route = await plan_route_uc.execute(
            PlanRouteRequest(profile_id=profile.id, activity_type=ActivityType.RUNNING)
        )
        stored = await route_repo.get_by_id(route.id)
        assert stored is not None
        assert stored.id == route.id
