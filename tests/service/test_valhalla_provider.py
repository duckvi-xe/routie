"""Tests for the Valhalla route provider."""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest

from routie.domain.enums import ActivityType, Direction, SkillLevel
from routie.domain.models import RoutePlanRequest, UserProfile
from routie.domain.value_objects import Coordinates
from routie.service.providers.polyline import decode_polyline

# ---------------------------------------------------------------------------
#  Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner_profile() -> UserProfile:
    return UserProfile.new(
        name="Runner",
        activity_type=ActivityType.RUNNING,
        skill_level=SkillLevel.INTERMEDIATE,
        home_coordinates=Coordinates(latitude=45.4642, longitude=9.1900),  # Milan
    )


@pytest.fixture
def cyclist_profile() -> UserProfile:
    return UserProfile.new(
        name="Cyclist",
        activity_type=ActivityType.CYCLING,
        skill_level=SkillLevel.ADVANCED,
        home_coordinates=Coordinates(latitude=45.4642, longitude=9.1900),  # Milan
    )


# ---------------------------------------------------------------------------
#  Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestVehicleMapping:
    def test_running_is_pedestrian(self) -> None:
        from routie.service.providers.valhalla import _vehicle_for_activity
        assert _vehicle_for_activity(ActivityType.RUNNING) == "pedestrian"

    def test_cycling_is_bicycle(self) -> None:
        from routie.service.providers.valhalla import _vehicle_for_activity
        assert _vehicle_for_activity(ActivityType.CYCLING) == "bicycle"


class TestBuildPayload:
    def test_basic_payload_structure(self) -> None:
        from routie.service.providers.valhalla import _build_valhalla_payload

        start = Coordinates(latitude=45.4642, longitude=9.1900)
        dest = Coordinates(latitude=45.5, longitude=9.2)

        payload = _build_valhalla_payload(start, dest, "pedestrian")

        assert payload["costing"] == "pedestrian"
        assert len(payload["locations"]) == 2
        assert payload["locations"][0] == {"lat": 45.4642, "lon": 9.1900}
        assert payload["locations"][1] == {"lat": 45.5, "lon": 9.2}
        assert payload["format"] == "json"
        assert "costing_options" in payload

    def test_pedestrian_costing_options(self) -> None:
        from routie.service.providers.valhalla import _build_valhalla_payload

        start = Coordinates(latitude=45.4642, longitude=9.1900)
        dest = Coordinates(latitude=45.5, longitude=9.2)

        payload = _build_valhalla_payload(start, dest, "pedestrian")
        opts = payload["costing_options"]["pedestrian"]
        assert opts["elevation_interval"] > 0
        assert opts["walking_speed"] > 0

    def test_bicycle_costing_options(self) -> None:
        from routie.service.providers.valhalla import _build_valhalla_payload

        start = Coordinates(latitude=45.4642, longitude=9.1900)
        dest = Coordinates(latitude=45.5, longitude=9.2)

        payload = _build_valhalla_payload(start, dest, "bicycle")
        opts = payload["costing_options"]["bicycle"]
        assert opts["elevation_interval"] > 0
        assert opts["cycling_speed"] > 0

    def test_payload_with_elevation_interval(self) -> None:
        from routie.service.providers.valhalla import _build_valhalla_payload

        start = Coordinates(latitude=45.4642, longitude=9.1900)
        dest = Coordinates(latitude=45.5, longitude=9.2)

        payload = _build_valhalla_payload(start, dest, "pedestrian", elevation_interval=10.0)
        assert payload["costing_options"]["pedestrian"]["elevation_interval"] == 10.0


class TestBuildDestination:
    def test_north_destination(self) -> None:
        from routie.service.providers.valhalla import _build_destination

        start = Coordinates(latitude=45.0, longitude=9.0)
        dest = _build_destination(start, 10.0, Direction.N)

        # Should be ~10km north: latitude increases, longitude stable
        assert dest.latitude > start.latitude  # north = higher lat
        assert abs(dest.longitude - start.longitude) < 0.1  # roughly stable

    def test_east_destination(self) -> None:
        from routie.service.providers.valhalla import _build_destination

        start = Coordinates(latitude=45.0, longitude=9.0)
        dest = _build_destination(start, 10.0, Direction.E)

        # Should be ~10km east: longitude increases
        assert dest.longitude > start.longitude
        assert abs(dest.latitude - start.latitude) < 0.1

    def test_distance_roughly_correct(self) -> None:
        from routie.service.providers.valhalla import _build_destination

        start = Coordinates(latitude=45.0, longitude=9.0)
        dest = _build_destination(start, 10.0, Direction.N)

        dist = start.distance_to(dest)
        # Flat-earth approximation: should be close to 10km
        assert 9.0 < dist < 11.0


class TestParseResponse:
    def test_parses_basic_route(self) -> None:
        from routie.service.providers.valhalla import _parse_valhalla_response

        # Simulated Valhalla response
        data = {
            "trip": {
                "locations": [{"lat": 45.4642, "lon": 9.1900}, {"lat": 45.5, "lon": 9.2}],
                "legs": [
                    {
                        "shape": [
                            [45.4642, 9.1900, 120.0],
                            [45.47, 9.192, 125.0],
                            [45.48, 9.195, 130.0],
                            [45.5, 9.2, 140.0],
                        ],
                        "summary": {
                            "length": 5.2,
                            "time": 1560.0,
                            "up_hill": 45.0,
                            "down_hill": 25.0,
                        },
                    }
                ],
                "summary": {
                    "length": 5.2,
                    "time": 1560.0,
                    "up_hill": 45.0,
                    "down_hill": 25.0,
                },
            }
        }

        route = _parse_valhalla_response(data, ActivityType.RUNNING)

        assert route.name == "Run 5km"
        assert route.distance_km == 5.2
        assert route.elevation_gain_m == 45.0
        assert route.estimated_duration_min == 26  # 1560s / 60 = 26
        assert len(route.waypoints) == 4
        assert route.waypoints[0].latitude == 45.4642
        assert route.waypoints[0].longitude == 9.1900
        assert route.polyline is not None
        assert len(route.polyline) > 0

    def test_parses_cycling_route(self) -> None:
        from routie.service.providers.valhalla import _parse_valhalla_response

        data = {
            "trip": {
                "locations": [{"lat": 45.4642, "lon": 9.1900}, {"lat": 45.48, "lon": 9.22}],
                "legs": [
                    {
                        "shape": [[45.4642, 9.1900], [45.48, 9.22]],
                        "summary": {
                            "length": 15.8,
                            "time": 2700.0,
                            "up_hill": 120.0,
                            "down_hill": 80.0,
                        },
                    }
                ],
                "summary": {
                    "length": 15.8,
                    "time": 2700.0,
                    "up_hill": 120.0,
                    "down_hill": 80.0,
                },
            }
        }

        route = _parse_valhalla_response(data, ActivityType.CYCLING)

        assert route.name == "Ride 16km"
        assert route.distance_km == 15.8
        assert route.elevation_gain_m == 120.0
        assert route.estimated_duration_min == 45  # 2700s / 60
        assert len(route.waypoints) == 2

    def test_polyline_roundtrip(self) -> None:
        from routie.service.providers.valhalla import _parse_valhalla_response

        data = {
            "trip": {
                "locations": [{"lat": 45.4642, "lon": 9.1900}, {"lat": 45.5, "lon": 9.2}],
                "legs": [
                    {
                        "shape": [
                            [45.4642, 9.1900, 100.0],
                            [45.47, 9.195, 110.0],
                            [45.48, 9.198, 120.0],
                            [45.5, 9.2, 130.0],
                        ],
                        "summary": {
                            "length": 5.0,
                            "time": 1500.0,
                            "up_hill": 30.0,
                            "down_hill": 0.0,
                        },
                    }
                ],
                "summary": {"length": 5.0, "time": 1500.0, "up_hill": 30.0, "down_hill": 0.0},
            }
        }

        route = _parse_valhalla_response(data, ActivityType.RUNNING)
        decoded = decode_polyline(route.polyline)

        assert len(decoded) == len(route.waypoints)
        for orig, dec in zip(route.waypoints, decoded, strict=True):
            assert abs(orig.latitude - dec[0]) < 0.00001
            assert abs(orig.longitude - dec[1]) < 0.00001

    def test_raises_on_empty_paths(self) -> None:
        from routie.service.providers.valhalla import (
            ValhallaError,
            _parse_valhalla_response,
        )

        data = {"trip": {"legs": []}}
        with pytest.raises(ValhallaError, match="No legs"):
            _parse_valhalla_response(data, ActivityType.RUNNING)

    def test_raises_on_empty_shape(self) -> None:
        from routie.service.providers.valhalla import (
            ValhallaError,
            _parse_valhalla_response,
        )

        data = {
            "trip": {
                "locations": [{"lat": 45.4642, "lon": 9.1900}, {"lat": 45.5, "lon": 9.2}],
                "legs": [
                    {
                        "shape": [],
                        "summary": {"length": 0, "time": 0, "up_hill": 0, "down_hill": 0},
                    }
                ],
                "summary": {"length": 0, "time": 0, "up_hill": 0, "down_hill": 0},
            }
        }
        with pytest.raises(ValhallaError, match="No coordinates"):
            _parse_valhalla_response(data, ActivityType.RUNNING)


class TestValhallaRouteProvider:
    """Integration-style tests for ValhallaRouteProvider with mocked HTTP client."""

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        client = AsyncMock(spec=httpx.AsyncClient)

        # Default successful response
        response = httpx.Response(
            status_code=200,
            json={
                "trip": {
                    "locations": [
                        {"lat": 45.4642, "lon": 9.1900},
                        {"lat": 45.5, "lon": 9.2},
                    ],
                    "legs": [
                        {
                            "shape": [
                                [45.4642, 9.1900, 120.0],
                                [45.47, 9.192, 125.0],
                                [45.48, 9.195, 130.0],
                                [45.5, 9.2, 140.0],
                            ],
                            "summary": {
                                "length": 5.2,
                                "time": 1560.0,
                                "up_hill": 45.0,
                                "down_hill": 25.0,
                            },
                        }
                    ],
                    "summary": {
                        "length": 5.2,
                        "time": 1560.0,
                        "up_hill": 45.0,
                        "down_hill": 25.0,
                    },
                }
            },
            request=httpx.Request("POST", "http://valhalla:8002/route"),
        )
        client.post.return_value = response
        return client

    @pytest.fixture
    def provider(self, mock_client: AsyncMock):
        from routie.service.providers.valhalla import ValhallaRouteProvider

        return ValhallaRouteProvider(client=mock_client)

    async def test_returns_route_with_valid_structure(
        self, provider, runner_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        route = await provider.plan_route(req, runner_profile)

        assert route.name
        assert route.distance_km == 5.2
        assert route.elevation_gain_m == 45.0
        assert route.estimated_duration_min == 26
        assert len(route.waypoints) >= 2
        assert route.polyline is not None

    async def test_sends_correct_payload(
        self, provider, mock_client: AsyncMock, runner_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        await provider.plan_route(req, runner_profile)

        # Check that the POST was made with the correct URL and payload
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # First positional arg is the URL
        url = call_args[0][0]
        assert "route" in url

        # The JSON payload should be passed
        payload = call_args.kwargs.get("json", {})
        assert payload["costing"] == "pedestrian"
        assert len(payload["locations"]) == 2
        assert payload["format"] == "json"

    async def test_uses_start_coordinates(
        self, provider, mock_client: AsyncMock, runner_profile: UserProfile
    ):
        start = Coordinates(latitude=41.9028, longitude=12.4964)  # Rome
        req = RoutePlanRequest(
            activity_type=ActivityType.RUNNING,
            start_coordinates=start,
        )
        await provider.plan_route(req, runner_profile)

        mock_client.post.assert_called_once()
        payload = mock_client.post.call_args.kwargs.get("json", {})
        first_loc = payload["locations"][0]
        assert first_loc["lat"] == 41.9028
        assert first_loc["lon"] == 12.4964

    async def test_cycling_route(
        self, provider, mock_client: AsyncMock, cyclist_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.CYCLING)
        await provider.plan_route(req, cyclist_profile)

        mock_client.post.assert_called_once()
        payload = mock_client.post.call_args.kwargs.get("json", {})
        assert payload["costing"] == "bicycle"

    async def test_polyline_is_populated(
        self, provider, runner_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        route = await provider.plan_route(req, runner_profile)
        assert route.polyline is not None
        assert len(route.polyline) > 0

    async def test_polyline_roundtrip_matches_waypoints(
        self, provider, runner_profile: UserProfile
    ):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        route = await provider.plan_route(req, runner_profile)
        decoded = decode_polyline(route.polyline)
        assert len(decoded) == len(route.waypoints)
        for orig, dec in zip(route.waypoints, decoded, strict=True):
            assert abs(orig.latitude - dec[0]) < 0.00001
            assert abs(orig.longitude - dec[1]) < 0.00001


class TestValhallaErrors:
    """Error handling tests for ValhallaRouteProvider."""

    @pytest.fixture
    def provider(self):
        from routie.service.providers.valhalla import ValhallaRouteProvider

        return ValhallaRouteProvider()

    async def test_raises_on_http_error(self, provider, runner_profile: UserProfile):
        """Simulates HTTP 500 from Valhalla."""
        client = AsyncMock(spec=httpx.AsyncClient)
        request_obj = httpx.Request("POST", "http://valhalla:8002/route")
        client.post.return_value = httpx.Response(
            status_code=500, text="Internal Server Error", request=request_obj
        )
        provider._client = client

        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        with pytest.raises(Exception, match="500"):
            await provider.plan_route(req, runner_profile)

    async def test_raises_on_connection_error(self, provider, runner_profile: UserProfile):
        """Simulates Valhalla being unreachable."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.post.side_effect = httpx.ConnectError("Connection refused")
        provider._client = client

        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        with pytest.raises(Exception, match="Connection refused"):
            await provider.plan_route(req, runner_profile)
