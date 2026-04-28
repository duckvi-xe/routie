"""Domain entities (models) for Routie."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from routie.domain.enums import (
    ActivityType,
    DifficultyLevel,
    Direction,
    SkillLevel,
    TerrainType,
)
from routie.domain.value_objects import Coordinates


@dataclass(frozen=True)
class UserProfile:
    """Immutable user profile entity."""

    id: UUID
    name: str
    activity_type: ActivityType
    skill_level: SkillLevel
    avg_speed_kmh: float
    max_distance_km: float | None
    preferred_terrain: TerrainType | None
    preferred_direction: Direction
    home_coordinates: Coordinates | None
    created_at: datetime

    @classmethod
    def new(
        cls,
        name: str,
        activity_type: ActivityType,
        *,
        skill_level: SkillLevel = SkillLevel.BEGINNER,
        avg_speed_kmh: float | None = None,
        max_distance_km: float | None = None,
        preferred_terrain: TerrainType | None = None,
        preferred_direction: Direction = Direction.ANY,
        home_coordinates: Coordinates | None = None,
    ) -> UserProfile:
        return cls(
            id=uuid4(),
            name=name,
            activity_type=activity_type,
            skill_level=skill_level,
            avg_speed_kmh=(
                avg_speed_kmh if avg_speed_kmh is not None else skill_level.default_speed_kmh
            ),
            max_distance_km=max_distance_km,
            preferred_terrain=preferred_terrain,
            preferred_direction=preferred_direction,
            home_coordinates=home_coordinates,
            created_at=datetime.now(tz=timezone.utc),
        )

    def with_speed(self, speed_kmh: float) -> UserProfile:
        """Return a copy with updated speed."""
        return UserProfile(
            id=self.id,
            name=self.name,
            activity_type=self.activity_type,
            skill_level=self.skill_level,
            avg_speed_kmh=speed_kmh,
            max_distance_km=self.max_distance_km,
            preferred_terrain=self.preferred_terrain,
            preferred_direction=self.preferred_direction,
            home_coordinates=self.home_coordinates,
            created_at=self.created_at,
        )

    def with_skill(self, skill_level: SkillLevel) -> UserProfile:
        """Return a copy with updated skill level (speed follows)."""
        return UserProfile(
            id=self.id,
            name=self.name,
            activity_type=self.activity_type,
            skill_level=skill_level,
            avg_speed_kmh=skill_level.default_speed_kmh,
            max_distance_km=self.max_distance_km,
            preferred_terrain=self.preferred_terrain,
            preferred_direction=self.preferred_direction,
            home_coordinates=self.home_coordinates,
            created_at=self.created_at,
        )

    def with_preferences(
        self,
        *,
        max_distance_km: float | None = None,
        preferred_terrain: TerrainType | None = None,
        preferred_direction: Direction | None = None,
    ) -> UserProfile:
        """Return a copy with updated preferences (None = keep current)."""
        return UserProfile(
            id=self.id,
            name=self.name,
            activity_type=self.activity_type,
            skill_level=self.skill_level,
            avg_speed_kmh=self.avg_speed_kmh,
            max_distance_km=max_distance_km if max_distance_km is not None else self.max_distance_km,
            preferred_terrain=preferred_terrain if preferred_terrain is not None else self.preferred_terrain,
            preferred_direction=preferred_direction if preferred_direction is not None else self.preferred_direction,
            home_coordinates=self.home_coordinates,
            created_at=self.created_at,
        )


@dataclass(frozen=True)
class RoutePlanRequest:
    """Immutable request for route planning."""

    activity_type: ActivityType
    max_distance_km: float | None = None
    max_duration_min: int | None = None
    preferred_direction: Direction | None = None
    terrain_type: TerrainType | None = None
    start_coordinates: Coordinates | None = None

    def __post_init__(self) -> None:
        if self.max_distance_km is not None and self.max_distance_km < 0:
            raise ValueError(
                f"max_distance_km must be non-negative, got {self.max_distance_km}"
            )
        if self.max_duration_min is not None and self.max_duration_min < 0:
            raise ValueError(
                f"max_duration_min must be non-negative, got {self.max_duration_min}"
            )


def _compute_difficulty(
    distance_km: float,
    elevation_gain_m: float,
    activity_type: ActivityType,
) -> DifficultyLevel:
    """Compute difficulty based on distance and elevation.

    Running and cycling use different scales — cycling is less strenuous
    per km and per meter of elevation.
    """
    if activity_type == ActivityType.CYCLING:
        effective_distance = distance_km * 0.5
        elevation_penalty = elevation_gain_m * 0.3
    else:
        effective_distance = distance_km
        elevation_penalty = elevation_gain_m

    score = effective_distance + elevation_penalty / 50.0

    if score < 12.0:
        return DifficultyLevel.EASY
    if score < 45.0:
        return DifficultyLevel.MODERATE
    return DifficultyLevel.HARD


@dataclass(frozen=True)
class Route:
    """Immutable route entity — the result of route planning."""

    id: UUID
    name: str
    activity_type: ActivityType
    distance_km: float
    elevation_gain_m: float
    estimated_duration_min: int
    difficulty: DifficultyLevel
    waypoints: list[Coordinates]
    polyline: str | None
    created_at: datetime

    @classmethod
    def new(
        cls,
        name: str,
        activity_type: ActivityType,
        *,
        distance_km: float,
        elevation_gain_m: float,
        estimated_duration_min: int,
        difficulty: DifficultyLevel | None = None,
        waypoints: list[Coordinates] | None = None,
        polyline: str | None = None,
    ) -> Route:
        return cls(
            id=uuid4(),
            name=name,
            activity_type=activity_type,
            distance_km=distance_km,
            elevation_gain_m=elevation_gain_m,
            estimated_duration_min=estimated_duration_min,
            difficulty=difficulty or _compute_difficulty(distance_km, elevation_gain_m, activity_type),
            waypoints=waypoints or [],
            polyline=polyline,
            created_at=datetime.now(tz=timezone.utc),
        )
