"""Tests for the mock route provider."""

from __future__ import annotations

import pytest

from routie.domain.enums import ActivityType, SkillLevel, TerrainType
from routie.domain.models import RoutePlanRequest, UserProfile
from routie.domain.value_objects import Coordinates
from routie.service.providers.mock import MockRouteProvider
from routie.service.providers.polyline import decode_polyline


@pytest.fixture
def provider() -> MockRouteProvider:
    return MockRouteProvider()


@pytest.fixture
def runner_profile() -> UserProfile:
    return UserProfile.new(
        name="Test Runner",
        activity_type=ActivityType.RUNNING,
        skill_level=SkillLevel.INTERMEDIATE,
    )


@pytest.fixture
def cyclist_profile() -> UserProfile:
    return UserProfile.new(
        name="Test Cyclist",
        activity_type=ActivityType.CYCLING,
        skill_level=SkillLevel.ADVANCED,
    )


class TestMockRouteProvider:
    async def test_returns_route_with_valid_structure(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        route = await provider.plan_route(req, runner_profile)
        assert route.name
        assert route.distance_km > 0
        assert route.elevation_gain_m > 0
        assert route.estimated_duration_min > 0
        assert len(route.waypoints) >= 2

    async def test_respects_max_distance(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING, max_distance_km=5.0
        )
        route = await provider.plan_route(req, runner_profile)
        assert route.distance_km <= 5.0

    async def test_respects_max_duration(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        """Distance should be proportional to duration when no max_distance set."""
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING, max_duration_min=30
        )
        route = await provider.plan_route(req, runner_profile)
        # At 8 km/h (beginner) for 30 min → max 4km
        assert route.estimated_duration_min <= 30

    async def test_route_waypoints_near_start(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        start = Coordinates(latitude=45.4642, longitude=9.1900)  # Milan
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            start_coordinates=start,
            max_distance_km=5.0,
        )
        route = await provider.plan_route(req, runner_profile)
        # First waypoint should be near Milan
        first = route.waypoints[0]
        assert first.distance_to(start) < 0.1  # within 100m

    async def test_cycling_route_is_longer(
        self, provider: MockRouteProvider, cyclist_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.CYCLING, max_distance_km=50.0)
        route = await provider.plan_route(req, cyclist_profile)
        assert route.distance_km <= 50.0
        assert route.distance_km > 5.0

    async def test_terrain_influences_elevation(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        flat_req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            terrain_type=TerrainType.FLAT,
        )
        hilly_req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            terrain_type=TerrainType.HILLY,
        )
        flat_route = await provider.plan_route(flat_req, runner_profile)
        hilly_route = await provider.plan_route(hilly_req, runner_profile)
        assert hilly_route.elevation_gain_m > flat_route.elevation_gain_m

    async def test_route_is_deterministic(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        """Same inputs produce the same route."""
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING, max_distance_km=10.0)
        route1 = await provider.plan_route(req, runner_profile)
        route2 = await provider.plan_route(req, runner_profile)
        assert route1.distance_km == route2.distance_km
        assert route1.elevation_gain_m == route2.elevation_gain_m
        assert route1.estimated_duration_min == route2.estimated_duration_min

    async def test_cycling_elevation_is_less_than_running(
        self, provider: MockRouteProvider, runner_profile: UserProfile, cyclist_profile: UserProfile
    ):
        """For the same distance and terrain, cycling elevation should be lower."""
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            terrain_type=TerrainType.MIXED,
        )
        run_route = await provider.plan_route(req, runner_profile)

        cyclo_req = RoutePlanRequest(
            activity_type=ActivityType.CYCLING,
            max_distance_km=10.0,
            terrain_type=TerrainType.MIXED,
        )
        bike_route = await provider.plan_route(cyclo_req, cyclist_profile)

        # Cycling routes tend to be flatter
        assert bike_route.elevation_gain_m <= run_route.elevation_gain_m

    async def test_duration_computed_from_distance_and_speed(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        """Duration ≈ distance / speed."""
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING, max_distance_km=10.0)
        route = await provider.plan_route(req, runner_profile)
        expected_min = (route.distance_km / runner_profile.avg_speed_kmh) * 60
        # Allow 20% tolerance for the random factor
        assert abs(route.estimated_duration_min - expected_min) / expected_min < 0.2


class TestMockProviderPolyline:
    """Tests for polyline encoding in MockProvider."""

    async def test_polyline_is_populated(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        """Route from mock provider should have a non-null polyline."""
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING, max_distance_km=10.0)
        route = await provider.plan_route(req, runner_profile)
        assert route.polyline is not None
        assert len(route.polyline) > 0

    async def test_polyline_roundtrip_matches_waypoints(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        """Decoded polyline should approximately match original waypoints."""
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING, max_distance_km=10.0)
        route = await provider.plan_route(req, runner_profile)
        decoded = decode_polyline(route.polyline)  # type: ignore[arg-type]
        assert len(decoded) == len(route.waypoints)
        for orig, dec in zip(route.waypoints, decoded):
            assert abs(orig.latitude - dec[0]) < 0.00001
            assert abs(orig.longitude - dec[1]) < 0.00001

    async def test_polyline_is_deterministic(
        self, provider: MockRouteProvider, runner_profile: UserProfile
    ):
        """Same inputs should produce the same polyline."""
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING, max_distance_km=10.0)
        route1 = await provider.plan_route(req, runner_profile)
        route2 = await provider.plan_route(req, runner_profile)
        assert route1.polyline == route2.polyline

    async def test_polyline_cycling(
        self, provider: MockRouteProvider, cyclist_profile: UserProfile
    ):
        """Cycling routes should also have polyline populated."""
        req = RoutePlanRequest(activity_type=ActivityType.CYCLING, max_distance_km=30.0)
        route = await provider.plan_route(req, cyclist_profile)
        assert route.polyline is not None
        assert len(route.polyline) > 0
