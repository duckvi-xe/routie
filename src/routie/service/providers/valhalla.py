"""Valhalla route provider — calls a Valhalla routing instance as a microservice.

This provider communicates with a Valhalla routing server via its HTTP API,
runs as a separate Docker container (port 8002 by default).

The provider:
1. Determines start coordinates (from request or profile home)
2. Builds a destination point based on direction and target distance
3. Calls Valhalla POST /route between start and destination
4. Parses the response into a domain Route entity

Valhalla profiles:
  - ``pedestrian`` → for running (with walking speed, elevation costing)
  - ``bicycle`` → for cycling (with cycling speed, elevation costing)
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from routie.domain.enums import ActivityType, Direction
from routie.domain.models import (
    Route,
    RoutePlanRequest,
    UserProfile,
    _compute_difficulty,
)
from routie.domain.value_objects import Coordinates
from routie.service.providers.base import RouteProvider
from routie.service.providers.polyline import encode_polyline

# km per degree of latitude (approx)
_KM_PER_DEG = 111.32

# Default starting location (Milan city center) — used when neither the request
# nor the profile provides start coordinates
_DEFAULT_START = Coordinates(latitude=45.4642, longitude=9.1900)

# Default Valhalla service URL when running in Docker compose
_DEFAULT_VALHALLA_URL = "http://valhalla:8002"


class ValhallaError(Exception):
    """Raised when Valhalla API call fails."""


def _vehicle_for_activity(activity_type: ActivityType) -> str:
    """Map Routie activity type to Valhalla costing profile."""
    return {ActivityType.RUNNING: "pedestrian", ActivityType.CYCLING: "bicycle"}[
        activity_type
    ]


def _build_destination(
    start: Coordinates,
    distance_km: float,
    direction: Direction,
) -> Coordinates:
    """Compute a destination point from start, distance, and direction.

    Uses a simplified flat-earth projection to determine the endpoint,
    which is then routed by Valhalla over real roads.
    """
    # Direction angle in degrees (clockwise from north)
    angle_map: dict[Direction, float] = {
        Direction.N: 0.0,
        Direction.NE: 45.0,
        Direction.E: 90.0,
        Direction.SE: 135.0,
        Direction.S: 180.0,
        Direction.SW: 225.0,
        Direction.W: 270.0,
        Direction.NW: 315.0,
        Direction.ANY: 45.0,  # default to northeast
    }
    bearing_deg = angle_map.get(direction, 45.0)
    bearing = math.radians(bearing_deg)

    dlat = (distance_km / _KM_PER_DEG) * math.cos(bearing)
    dlon = (
        (distance_km / (_KM_PER_DEG * math.cos(math.radians(start.latitude))))
        * math.sin(bearing)
    )

    return Coordinates(
        latitude=start.latitude + dlat,
        longitude=start.longitude + dlon,
    )


def _build_valhalla_payload(
    start: Coordinates,
    destination: Coordinates,
    costing: str,
    *,
    elevation_interval: float = 10.0,
) -> dict:
    """Build the JSON payload for the Valhalla /route endpoint.

    Args:
        start: Start coordinates.
        destination: Destination coordinates.
        costing: Valhalla costing profile (pedestrian, bicycle, etc.).
        elevation_interval: Meters between elevation samples (0 = disabled).

    Returns:
        Dict ready to be serialized as JSON for the Valhalla API.
    """
    payload: dict = {
        "locations": [
            {"lat": start.latitude, "lon": start.longitude},
            {"lat": destination.latitude, "lon": destination.longitude},
        ],
        "costing": costing,
        "format": "json",
        "directions_options": {"units": "kilometers"},
    }

    # Add costing options with elevation interval
    costing_options: dict = {}
    if costing == "pedestrian":
        costing_options = {
            "walking_speed": 5.1,
            "elevation_interval": elevation_interval,
        }
    elif costing == "bicycle":
        costing_options = {
            "cycling_speed": 15.0,
            "use_hills": 0.5,
            "elevation_interval": elevation_interval,
        }

    if elevation_interval > 0:
        payload["costing_options"] = {costing: costing_options}

    return payload


def _parse_valhalla_response(
    data: dict,
    activity_type: ActivityType,
) -> Route:
    """Parse a Valhalla /route response into a domain Route entity.

    Valhalla returns the route shape as an array of [lat, lon, elevation?] tuples
    under ``trip.legs[0].shape``, and summary stats (distance in km, time in
    seconds, elevation gain/loss in meters) under ``trip.legs[0].summary``.

    Args:
        data: Raw JSON response from Valhalla /route.
        activity_type: The activity type for difficulty computation.

    Returns:
        A Route domain entity.

    Raises:
        ValhallaError: If the response is malformed or missing required fields.
    """
    trip = data.get("trip")
    if not trip:
        raise ValhallaError("Missing 'trip' in Valhalla response")

    legs = trip.get("legs", [])
    if not legs:
        raise ValhallaError("No legs in Valhalla response")

    leg = legs[0]

    # Distance: already in km
    summary = leg.get("summary", {})
    distance_km = summary.get("length", 0.0)

    # Time: seconds → minutes
    time_s = summary.get("time", 0)
    duration_min = max(1, round(time_s / 60.0))

    # Elevation: meters
    elevation_gain_m = summary.get("up_hill", 0.0)

    # Shape: [lat, lon, elevation?] → Coordinates(lat, lon)
    shape: list[list[float]] = leg.get("shape", [])
    if not shape:
        raise ValhallaError("No coordinates in Valhalla response")

    waypoints = [
        Coordinates(latitude=pt[0], longitude=pt[1]) for pt in shape
    ]

    # Compute difficulty
    difficulty = _compute_difficulty(distance_km, elevation_gain_m, activity_type)

    # Encode polyline from waypoints
    polyline = encode_polyline(waypoints)

    # Build name
    vehicle_label = "Run" if activity_type == ActivityType.RUNNING else "Ride"
    name = f"{vehicle_label} {round(distance_km)}km"

    return Route(
        id=uuid4(),
        name=name,
        activity_type=activity_type,
        distance_km=round(distance_km, 2),
        elevation_gain_m=round(elevation_gain_m, 1),
        estimated_duration_min=duration_min,
        difficulty=difficulty,
        waypoints=waypoints,
        polyline=polyline,
        created_at=datetime.now(tz=UTC),
    )


class ValhallaRouteProvider(RouteProvider):
    """Route provider that calls a Valhalla instance via its HTTP API.

    The provider:
    - Communicates with Valhalla on its default port 8002
    - Computes a destination point using direction and distance constraints
    - Delegates actual road routing to Valhalla
    - Returns a domain Route with real road data (distance, elevation, waypoints)

    Args:
        base_url: Valhalla API base URL (default: http://valhalla:8002).
        client: Optional httpx.AsyncClient (for DI/testing).
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_VALHALLA_URL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: UserProfile,
    ) -> Route:
        """Plan a route by calling Valhalla between start and destination.

        Args:
            request: Route planning request with activity, distance, direction.
            profile: User profile with skill level, home coordinates.

        Returns:
            A Route with real road data from Valhalla.

        Raises:
            ValhallaError: If Valhalla is unreachable or returns an error.
        """
        # Determine start coordinates
        start = request.start_coordinates or profile.home_coordinates or _DEFAULT_START

        # Determine target distance
        target_km = request.max_distance_km
        if target_km is None and request.max_duration_min is not None:
            target_km = (request.max_duration_min / 60.0) * profile.avg_speed_kmh
        if target_km is None:
            target_km = profile.max_distance_km
        if target_km is None:
            target_km = (
                10.0 if request.activity_type == ActivityType.RUNNING else 30.0
            )

        # Clamp to max duration if both are set
        if request.max_duration_min is not None:
            max_by_duration = (
                request.max_duration_min / 60.0
            ) * profile.avg_speed_kmh
            target_km = min(target_km, max_by_duration)

        # Determine direction
        direction = (
            request.preferred_direction
            or profile.preferred_direction
            or Direction.ANY
        )

        # Build destination point
        destination = _build_destination(start, target_km, direction)

        # Determine costing profile
        costing = _vehicle_for_activity(request.activity_type)

        # Build request payload
        payload = _build_valhalla_payload(start, destination, costing)

        # Build URL
        url = f"{self._base_url}/route"

        # Call Valhalla
        try:
            response = await self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise ValhallaError(
                f"Valhalla returned HTTP {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise ValhallaError(
                f"Valhalla connection failed: {e}"
            ) from e

        # Parse response
        route = _parse_valhalla_response(data, request.activity_type)
        return route
