"""GraphHopper route provider — calls a GraphHopper instance as a microservice.

This provider communicates with a GraphHopper routing server via its HTTP API,
runs as a separate Docker container (graphhopper:8989 by default).

The provider:
1. Determines start coordinates (from request or profile home)
2. Builds a destination point based on direction and target distance
3. Calls GraphHopper /route API between start and destination
4. Parses the response into a domain Route entity
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from routie.domain.enums import (
    ActivityType,
    Direction,
)
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

# Default GraphHopper service URL when running in Docker compose
_DEFAULT_GRAPHOPPER_URL = "http://graphhopper:8989"


class GraphHopperError(Exception):
    """Raised when GraphHopper API call fails."""


def _vehicle_for_activity(activity_type: ActivityType) -> str:
    """Map Routie activity type to GraphHopper vehicle."""
    return {ActivityType.RUNNING: "foot", ActivityType.CYCLING: "bike"}[activity_type]


def _build_graphhopper_url(
    start: Coordinates,
    destination: Coordinates,
    vehicle: str,
    base_url: str = _DEFAULT_GRAPHOPPER_URL,
    api_key: str | None = None,
) -> str:
    """Build the GraphHopper /route URL with query parameters."""
    params = [
        f"point={start.latitude},{start.longitude}",
        f"point={destination.latitude},{destination.longitude}",
        f"vehicle={vehicle}",
        "elevation=true",
        "points_encoded=false",
        "instructions=false",
    ]
    if api_key:
        params.append(f"key={api_key}")
    return f"{base_url}/route?{'&'.join(params)}"


def _build_destination(
    start: Coordinates,
    distance_km: float,
    direction: Direction,
) -> Coordinates:
    """Compute a destination point from start, distance, and direction.

    Uses a simplified flat-earth projection to determine the endpoint,
    which is then routed by GraphHopper over real roads.
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
    dlon = (distance_km / (_KM_PER_DEG * math.cos(math.radians(start.latitude)))) * math.sin(
        bearing
    )

    return Coordinates(
        latitude=start.latitude + dlat,
        longitude=start.longitude + dlon,
    )


def _parse_graphhopper_response(
    data: dict,
    activity_type: ActivityType,
) -> Route:
    """Parse a GraphHopper /route response into a domain Route entity.

    GraphHopper returns coordinates as [longitude, latitude] (GeoJSON format).
    This function converts them to (latitude, longitude) for the domain model.

    Args:
        data: Raw JSON response from GraphHopper /route.
        activity_type: The activity type for difficulty computation.

    Returns:
        A Route domain entity.

    Raises:
        GraphHopperError: If the response is malformed or missing required fields.
    """
    paths = data.get("paths")
    if not paths:
        raise GraphHopperError("No paths in GraphHopper response")

    path = paths[0]

    # Distance: meters → km
    distance_m = path.get("distance", 0.0)
    distance_km = distance_m / 1000.0

    # Time: ms → minutes
    time_ms = path.get("time", 0)
    duration_min = max(1, round(time_ms / 60000.0))

    # Elevation: meters
    elevation_gain_m = path.get("ascent", 0.0)

    # Coordinates: [lon, lat] → Coordinates(lat, lon)
    points_data = path.get("points", {})
    coordinates_raw: list[list[float]] = points_data.get("coordinates", [])
    if not coordinates_raw:
        raise GraphHopperError("No coordinates in GraphHopper response")

    waypoints = [
        Coordinates(latitude=coord[1], longitude=coord[0])
        for coord in coordinates_raw
    ]

    # Compute difficulty
    difficulty = _compute_difficulty(distance_km, elevation_gain_m, activity_type)

    # Encode polyline
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


class GraphHopperRouteProvider(RouteProvider):
    """Route provider that calls a GraphHopper instance via its HTTP API.

    The provider:
    - Communicates with GraphHopper on its default port 8989
    - Computes a destination point using direction and distance constraints
    - Delegates actual road routing to GraphHopper
    - Returns a domain Route with real road data (distance, elevation, waypoints)

    Args:
        base_url: GraphHopper API base URL (default: http://graphhopper:8989).
        api_key: Optional API key for hosted GraphHopper instances.
        client: Optional httpx AsyncClient (for DI/testing).
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_GRAPHOPPER_URL,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: UserProfile,
    ) -> Route:
        """Plan a route by calling GraphHopper between start and destination.

        Args:
            request: Route planning request with activity, distance, direction.
            profile: User profile with skill level, home coordinates.

        Returns:
            A Route with real road data from GraphHopper.

        Raises:
            GraphHopperError: If GraphHopper is unreachable or returns an error.
        """
        # Determine start coordinates
        start = request.start_coordinates or profile.home_coordinates
        if start is None:
            raise GraphHopperError(
                "start coordinates are required — set start_coordinates in the "
                "request or home_coordinates in the profile"
            )

        # Determine target distance
        target_km = request.max_distance_km
        if target_km is None and request.max_duration_min is not None:
            target_km = (request.max_duration_min / 60.0) * profile.avg_speed_kmh
        if target_km is None:
            target_km = profile.max_distance_km
        if target_km is None:
            target_km = 10.0 if request.activity_type == ActivityType.RUNNING else 30.0

        # Clamp to max duration if both are set
        if request.max_duration_min is not None:
            max_by_duration = (request.max_duration_min / 60.0) * profile.avg_speed_kmh
            target_km = min(target_km, max_by_duration)

        # Determine direction
        direction = request.preferred_direction or profile.preferred_direction or Direction.ANY

        # Build destination point
        destination = _build_destination(start, target_km, direction)

        # Determine vehicle
        vehicle = _vehicle_for_activity(request.activity_type)

        # Build URL
        url = _build_graphhopper_url(
            start=start,
            destination=destination,
            vehicle=vehicle,
            base_url=self._base_url,
            api_key=self._api_key,
        )

        # Call GraphHopper
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            raise GraphHopperError(
                f"GraphHopper returned HTTP {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise GraphHopperError(
                f"GraphHopper connection failed: {e}"
            ) from e

        # Parse response
        route = _parse_graphhopper_response(data, request.activity_type)
        return route
