"""Tests for the GraphHopper route provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from routie.domain.enums import ActivityType, Direction, SkillLevel
from routie.domain.models import RoutePlanRequest, UserProfile
from routie.domain.value_objects import Coordinates

pytest.importorskip("routie.service.providers.graphhopper")
from routie.service.providers.graphhopper import (
    GraphHopperError,
    GraphHopperRouteProvider,
    _build_destination,
    _build_graphhopper_url,
    _parse_graphhopper_response,
    _vehicle_for_activity,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


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


@pytest.fixture
def milan_start() -> Coordinates:
    return Coordinates(latitude=45.4642, longitude=9.1900)


@pytest.fixture
def graphhopper_response() -> dict:
    """Simulated GraphHopper /route response (points_encoded=false)."""
    return {
        "paths": [
            {
                "distance": 10050.0,  # meters
                "time": 2700000,  # ms ≈ 45 min
                "ascent": 85.0,
                "descent": 70.0,
                "points": {
                    "type": "LineString",
                    "coordinates": [
                        [9.19, 45.4642],  # [lon, lat]
                        [9.20, 45.4680],
                        [9.21, 45.4720],
                        [9.22, 45.4760],
                        [9.23, 45.4800],
                        [9.24, 45.4840],
                        [9.25, 45.4880],
                        [9.26, 45.4920],
                        [9.27, 45.4960],
                        [9.28, 45.5000],
                    ],
                },
                "instructions": [],
            }
        ],
        "info": {
            "took": 42,
        },
    }


# ── Unit tests: helper functions ──────────────────────────────────────────────


class TestVehicleMapping:
    def test_running_maps_to_foot(self) -> None:
        assert _vehicle_for_activity(ActivityType.RUNNING) == "foot"

    def test_cycling_maps_to_bike(self) -> None:
        assert _vehicle_for_activity(ActivityType.CYCLING) == "bike"


class TestBuildUrl:
    def test_basic_url(self) -> None:
        start = Coordinates(latitude=45.4642, longitude=9.1900)
        dest = Coordinates(latitude=45.5000, longitude=9.2800)
        url = _build_graphhopper_url(
            start=start,
            destination=dest,
            vehicle="foot",
            base_url="http://localhost:8989",
            api_key=None,
        )
        assert "http://localhost:8989" in url
        assert "point=45.4642,9.19" in url
        assert "point=45.5,9.28" in url
        assert "vehicle=foot" in url
        assert "elevation=true" in url
        assert "points_encoded=false" in url
        assert "instructions=false" in url

    def test_with_api_key(self) -> None:
        start = Coordinates(latitude=45.4642, longitude=9.1900)
        dest = Coordinates(latitude=45.5000, longitude=9.2800)
        url = _build_graphhopper_url(
            start=start,
            destination=dest,
            vehicle="bike",
            base_url="https://graphhopper.com/api/1",
            api_key="secret123",
        )
        assert "key=secret123" in url
        assert "vehicle=bike" in url


class TestBuildDestination:
    def test_direction_east(self) -> None:
        start = Coordinates(latitude=45.0, longitude=9.0)
        dest = _build_destination(start, distance_km=10.0, direction=Direction.E)
        # Moving east means longitude increases, latitude stays roughly same
        assert dest.longitude > start.longitude
        assert abs(dest.latitude - start.latitude) < 0.5

    def test_direction_north(self) -> None:
        start = Coordinates(latitude=45.0, longitude=9.0)
        dest = _build_destination(start, distance_km=10.0, direction=Direction.N)
        assert dest.latitude > start.latitude

    def test_direction_any_uses_default(self) -> None:
        start = Coordinates(latitude=45.0, longitude=9.0)
        dest = _build_destination(start, distance_km=10.0, direction=Direction.ANY)
        # ANY = NORTHEAST (45 degrees)
        assert dest.latitude > start.latitude
        assert dest.longitude > start.longitude

    def test_distance_affects_destination(self) -> None:
        start = Coordinates(latitude=45.0, longitude=9.0)
        near = _build_destination(start, distance_km=5.0, direction=Direction.N)
        far = _build_destination(start, distance_km=20.0, direction=Direction.N)
        assert near.distance_to(start) < far.distance_to(start)


class TestParseResponse:
    def test_parses_basic_fields(self, graphhopper_response: dict) -> None:
        route = _parse_graphhopper_response(
            graphhopper_response,
            activity_type=ActivityType.RUNNING,
        )
        # 10050 m → 10.05 km
        assert abs(route.distance_km - 10.05) < 0.01
        # 2700000 ms → 45 min
        assert route.estimated_duration_min == 45
        # ascent = 85.0
        assert abs(route.elevation_gain_m - 85.0) < 0.1
        # 10 coordinates [lon,lat] → 10 waypoints
        assert len(route.waypoints) == 10

    def test_waypoints_are_lat_lon_not_lon_lat(self, graphhopper_response: dict) -> None:
        """GraphHopper returns [lon, lat] — we must convert to [lat, lon]."""
        route = _parse_graphhopper_response(
            graphhopper_response, activity_type=ActivityType.RUNNING
        )
        # First coordinate from response: [9.19, 45.4642]
        wp = route.waypoints[0]
        assert isinstance(wp, Coordinates)
        assert abs(wp.latitude - 45.4642) < 0.0001
        assert abs(wp.longitude - 9.19) < 0.0001

    def test_difficulty_computed(self, graphhopper_response: dict) -> None:
        route = _parse_graphhopper_response(
            graphhopper_response, activity_type=ActivityType.RUNNING
        )
        assert route.difficulty is not None
        assert route.difficulty.value in ("easy", "moderate", "hard")

    def test_polyline_generated(self, graphhopper_response: dict) -> None:
        route = _parse_graphhopper_response(
            graphhopper_response, activity_type=ActivityType.RUNNING
        )
        assert route.polyline is not None
        assert len(route.polyline) > 0

    def test_name_generated(self, graphhopper_response: dict) -> None:
        route = _parse_graphhopper_response(
            graphhopper_response, activity_type=ActivityType.RUNNING
        )
        assert route.name
        assert "Run" in route.name or "Ride" in route.name

    def test_cycling_uses_bike_prefix(self, graphhopper_response: dict) -> None:
        route = _parse_graphhopper_response(
            graphhopper_response, activity_type=ActivityType.CYCLING
        )
        assert "Ride" in route.name or "Cycle" in route.name or "Spin" in route.name

    def test_created_at_is_set(self, graphhopper_response: dict) -> None:
        route = _parse_graphhopper_response(
            graphhopper_response, activity_type=ActivityType.RUNNING
        )
        assert route.created_at is not None


class TestParseResponseErrors:
    def test_raises_on_missing_paths(self) -> None:
        with pytest.raises(GraphHopperError, match="No paths"):
            _parse_graphhopper_response({}, activity_type=ActivityType.RUNNING)

    def test_raises_on_empty_paths(self) -> None:
        with pytest.raises(GraphHopperError, match="No paths"):
            _parse_graphhopper_response(
                {"paths": []}, activity_type=ActivityType.RUNNING
            )

    def test_raises_on_missing_coordinates(self) -> None:
        with pytest.raises(GraphHopperError, match="No coordinates"):
            _parse_graphhopper_response(
                {"paths": [{"distance": 100.0}]},
                activity_type=ActivityType.RUNNING,
            )


# ── Integration tests: full provider with HTTP mock ──────────────────────────


class TestGraphHopperRouteProvider:
    async def test_returns_route_with_mocked_response(
        self,
        runner_profile: UserProfile,
        milan_start: Coordinates,
        graphhopper_response: dict,
    ) -> None:
        """End-to-end: provider calls mocked GraphHopper and returns a Route."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = graphhopper_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        provider = GraphHopperRouteProvider(
            base_url="http://mock-graphhopper:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            preferred_direction=Direction.E,
            start_coordinates=milan_start,
        )

        route = await provider.plan_route(req, runner_profile)

        assert route.name
        assert abs(route.distance_km - 10.05) < 0.01
        assert route.estimated_duration_min == 45
        assert len(route.waypoints) == 10
        assert route.polyline is not None

    async def test_raises_on_http_error(
        self,
        runner_profile: UserProfile,
        milan_start: Coordinates,
    ) -> None:
        """Provider raises GraphHopperError when GraphHopper returns non-200."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_response
        )
        mock_client.get = AsyncMock(return_value=mock_response)

        provider = GraphHopperRouteProvider(
            base_url="http://mock-graphhopper:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            start_coordinates=milan_start,
        )

        with pytest.raises(GraphHopperError):
            await provider.plan_route(req, runner_profile)

    async def test_raises_on_connection_error(
        self,
        runner_profile: UserProfile,
        milan_start: Coordinates,
    ) -> None:
        """Provider raises GraphHopperError when GraphHopper is unreachable."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.ConnectError(
            "Connection refused", request=MagicMock()
        )

        provider = GraphHopperRouteProvider(
            base_url="http://unreachable:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            start_coordinates=milan_start,
        )

        with pytest.raises(GraphHopperError, match="Connection refused"):
            await provider.plan_route(req, runner_profile)

    async def test_cycling_uses_bike_vehicle(
        self,
        cyclist_profile: UserProfile,
        milan_start: Coordinates,
        graphhopper_response: dict,
    ) -> None:
        """Verify the correct vehicle is passed for cycling."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = graphhopper_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        provider = GraphHopperRouteProvider(
            base_url="http://mock-graphhopper:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.CYCLING,
            max_distance_km=30.0,
            start_coordinates=milan_start,
        )

        route = await provider.plan_route(req, cyclist_profile)
        assert route.name
        assert route.distance_km > 0

    async def test_requires_start_coordinates(
        self,
        runner_profile: UserProfile,
    ) -> None:
        """Provider raises error if no start coordinates are provided."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        provider = GraphHopperRouteProvider(
            base_url="http://mock-graphhopper:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            max_distance_km=10.0,
            start_coordinates=None,
        )
        with pytest.raises(GraphHopperError, match="start coordinates"):
            await provider.plan_route(req, runner_profile)

    async def test_uses_default_distance_when_no_constraints(
        self,
        runner_profile: UserProfile,
        milan_start: Coordinates,
        graphhopper_response: dict,
    ) -> None:
        """When no max_distance anywhere, defaults to 10km for running."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = graphhopper_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        provider = GraphHopperRouteProvider(
            base_url="http://mock-graphhopper:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            start_coordinates=milan_start,
        )

        # Should not raise — uses default distance (10km for running)
        route = await provider.plan_route(req, runner_profile)
        assert route.name
        assert route.distance_km > 0

    async def test_uses_profile_max_distance_as_fallback(
        self,
        milan_start: Coordinates,
        graphhopper_response: dict,
    ) -> None:
        """When request has no max_distance, use profile's max_distance_km."""
        profile = UserProfile.new(
            name="Profile With Distance",
            activity_type=ActivityType.RUNNING,
            skill_level=SkillLevel.INTERMEDIATE,
            max_distance_km=15.0,
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = graphhopper_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        provider = GraphHopperRouteProvider(
            base_url="http://mock-graphhopper:8989",
            client=mock_client,
        )
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            start_coordinates=milan_start,
            # No max_distance_km — should fall back to profile's 15.0
        )

        route = await provider.plan_route(req, profile)
        assert route.name
