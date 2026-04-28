"""Mock route provider — generates plausible routes algorithmically.

This provider does NOT call any external API. It creates a route by:

1. Determining target distance (from request constraints or profile defaults)
2. Generating waypoints in the chosen direction with controlled randomness
3. Computing elevation based on terrain type
4. Estimating duration from distance and user speed

The result is deterministic for identical inputs (using hashed seed).
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from uuid import uuid4

from routie.domain.enums import (
    ActivityType,
    Direction,
    TerrainType,
)
from routie.domain.models import Route, RoutePlanRequest, UserProfile
from routie.domain.models import _compute_difficulty
from routie.domain.value_objects import Coordinates
from routie.service.providers.base import RouteProvider


# Default starting location (Milan city center)
_DEFAULT_START = Coordinates(latitude=45.4642, longitude=9.1900)

# km per degree of latitude (approx)
_KM_PER_DEG = 111.32


def _compute_seed(request: RoutePlanRequest, profile: UserProfile) -> int:
    """Deterministic hash from request + profile for reproducible routes."""
    raw = (
        f"{request.activity_type.value}:"
        f"{request.max_distance_km}:"
        f"{request.max_duration_min}:"
        f"{request.preferred_direction}:"
        f"{request.terrain_type}:"
        f"{profile.skill_level.value}:"
        f"{profile.avg_speed_kmh}"
    )
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _seeded_float(seed: int, index: int) -> float:
    """Deterministic pseudo-random float in [0, 1)."""
    h = hashlib.sha256(f"{seed}:{index}".encode()).hexdigest()
    return int(h[:16], 16) / (2**64)


def _seeded_range(seed: int, index: int, lo: float, hi: float) -> float:
    return lo + _seeded_float(seed, index) * (hi - lo)


class MockRouteProvider(RouteProvider):
    """Route provider that generates routes algorithmically — no API needed."""

    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: UserProfile,
    ) -> Route:
        seed = _compute_seed(request, profile)

        # --- Determine target distance ---
        target_distance_km = request.max_distance_km
        if target_distance_km is None and request.max_duration_min is not None:
            # Derive distance from max duration and speed
            target_distance_km = (request.max_duration_min / 60.0) * profile.avg_speed_kmh
        if target_distance_km is None:
            # Fallback to profile preference
            target_distance_km = profile.max_distance_km
        if target_distance_km is None:
            # Final fallback: default based on activity type
            target_distance_km = 10.0 if request.activity_type == ActivityType.RUNNING else 30.0

        # Clamp to max duration if both are set
        if (
            request.max_duration_min is not None
        ):
            max_by_duration = (request.max_duration_min / 60.0) * profile.avg_speed_kmh
            target_distance_km = min(target_distance_km, max_by_duration)

        # --- Determine direction ---
        preferred_direction = (
            request.preferred_direction
            or profile.preferred_direction
            or Direction.ANY
        )

        # --- Determine terrain ---
        terrain = request.terrain_type or profile.preferred_terrain or TerrainType.MIXED

        # --- Determine start ---
        start = request.start_coordinates or profile.home_coordinates or _DEFAULT_START

        # --- Generate waypoints ---
        waypoints = self._generate_waypoints(
            start, target_distance_km, preferred_direction, seed
        )

        # --- Compute actual distance from waypoints ---
        actual_distance_km = self._compute_path_distance(waypoints)

        # --- Determine elevation ---
        elevation_gain_m = self._compute_elevation(
            actual_distance_km, terrain, request.activity_type, seed
        )

        # --- Estimate duration ---
        estimated_duration_min = max(
            1, round((actual_distance_km / profile.avg_speed_kmh) * 60.0)
        )

        # --- Determine difficulty ---
        difficulty = _compute_difficulty(
            actual_distance_km, elevation_gain_m, request.activity_type
        )

        # --- Build name ---
        name = self._generate_name(
            request.activity_type, actual_distance_km, terrain, seed
        )

        return Route(
            id=uuid4(),
            name=name,
            activity_type=request.activity_type,
            distance_km=round(actual_distance_km, 2),
            elevation_gain_m=round(elevation_gain_m, 1),
            estimated_duration_min=estimated_duration_min,
            difficulty=difficulty,
            waypoints=waypoints,
            polyline=None,
            created_at=datetime.now(tz=timezone.utc),
        )

    def _generate_waypoints(
        self,
        start: Coordinates,
        target_km: float,
        direction: Direction,
        seed: int,
        min_segments: int = 5,
        max_segments: int = 12,
    ) -> list[Coordinates]:
        """Generate a list of waypoints forming a route not exceeding target_km.

        Uses an iterative approach: generates segments, computes actual
        Haversine distance, and scales down if necessary.
        """
        n_segments = max(min_segments, min(max_segments, round(target_km / 1.5 + 2)))

        # Base bearing in radians
        if direction == Direction.ANY or direction.angle is None:
            bearing_deg = _seeded_range(seed, 0, 0, 360)
        else:
            bearing_deg = float(direction.angle)
        base_bearing = math.radians(bearing_deg)

        # Generate bearings and raw lengths
        bearings: list[float] = []
        raw_lengths: list[float] = []
        for i in range(n_segments):
            deviation = _seeded_range(seed, i + 1, -30, 30)
            bearings.append(base_bearing + math.radians(deviation))
            raw_lengths.append(_seeded_range(seed, i + 100, 0.6, 1.4))

        # Scale to target distance
        total_raw = sum(raw_lengths)
        scale = target_km / total_raw

        # Build waypoints with iterative scaling
        for attempt in range(5):
            scaled_lengths = [scale * l * 0.98 for l in raw_lengths]

            points: list[Coordinates] = [start]
            lat, lon = start.latitude, start.longitude

            for i in range(n_segments):
                seg_km = scaled_lengths[i]
                bearing = bearings[i]

                dlat = seg_km / _KM_PER_DEG * math.cos(bearing)
                dlon = seg_km / (
                    _KM_PER_DEG * math.cos(math.radians(lat + dlat / 2))
                )
                lat += dlat
                lon += dlon
                points.append(Coordinates(latitude=lat, longitude=lon))

            actual = self._compute_path_distance(points)
            if actual <= target_km or attempt == 4:
                return points
            # Scale down more aggressively
            scale *= target_km / actual

        return points

    def _compute_path_distance(self, waypoints: list[Coordinates]) -> float:
        """Sum of Haversine distances between consecutive waypoints."""
        total = 0.0
        for i in range(1, len(waypoints)):
            total += waypoints[i - 1].distance_to(waypoints[i])
        return total

    def _compute_elevation(
        self,
        distance_km: float,
        terrain: TerrainType,
        activity_type: ActivityType,
        seed: int,
    ) -> float:
        """Estimate elevation gain based on distance, terrain, and activity."""
        # Base elevation per km for each terrain
        base_per_km = {
            TerrainType.FLAT: 3.0,
            TerrainType.MIXED: 15.0,
            TerrainType.HILLY: 35.0,
        }[terrain]

        # Cycling routes tend to have less elevation gain per km
        if activity_type == ActivityType.CYCLING:
            base_per_km *= 0.7

        raw = distance_km * base_per_km
        # Add subtle random factor for realism (±15%)
        factor = _seeded_range(seed, 999, 0.85, 1.15)
        return raw * factor

    def _generate_name(
        self,
        activity_type: ActivityType,
        distance_km: float,
        terrain: TerrainType,
        seed: int,
    ) -> str:
        """Generate a human-readable route name."""
        prefixes = {
            ActivityType.RUNNING: ["Run", "Jog", "Trail"],
            ActivityType.CYCLING: ["Ride", "Cycle", "Spin"],
        }
        terrains = {
            TerrainType.FLAT: ["Flat", "Easy", "Pancake"],
            TerrainType.HILLY: ["Hilly", "Challenging", "Climb"],
            TerrainType.MIXED: ["Mixed", "Varied", "Scenic"],
        }

        prefix = prefixes[activity_type][round(_seeded_float(seed, 500) * 2)]
        terrain_word = terrains[terrain][round(_seeded_float(seed, 501) * 2)]
        km = round(distance_km)
        return f"{prefix} {terrain_word} {km}km"
