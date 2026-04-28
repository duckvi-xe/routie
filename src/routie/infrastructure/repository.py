"""SQLAlchemy-backed implementations of repository ports.

These replace ``InMemoryUserProfileRepository`` / ``InMemoryRouteRepository``
for production use. Each method opens and closes its own session.
"""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

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
from routie.infrastructure.orm import RouteModel, UserProfileModel
from routie.use_cases.manage_profile import UserProfileRepository
from routie.use_cases.plan_route import RouteRepository

# ---------------------------------------------------------------------------
#  Conversion helpers
# ---------------------------------------------------------------------------


def _profile_to_model(profile: UserProfile) -> UserProfileModel:
    """Convert a domain UserProfile to an ORM UserProfileModel."""
    return UserProfileModel(
        id=profile.id,
        name=profile.name,
        activity_type=profile.activity_type.value,
        skill_level=profile.skill_level.value,
        avg_speed_kmh=profile.avg_speed_kmh,
        max_distance_km=profile.max_distance_km,
        preferred_terrain=profile.preferred_terrain.value
        if profile.preferred_terrain
        else None,
        preferred_direction=profile.preferred_direction.value,
        home_latitude=profile.home_coordinates.latitude
        if profile.home_coordinates
        else None,
        home_longitude=profile.home_coordinates.longitude
        if profile.home_coordinates
        else None,
        created_at=profile.created_at,
    )


def _model_to_profile(model: UserProfileModel) -> UserProfile:
    """Convert an ORM UserProfileModel back to a domain UserProfile."""
    home_coords = None
    if model.home_latitude is not None and model.home_longitude is not None:
        home_coords = Coordinates(
            latitude=model.home_latitude, longitude=model.home_longitude
        )

    created_at = model.created_at
    # SQLite doesn't store timezone; assume UTC if missing
    if created_at.tzinfo is None:

        created_at = created_at.replace(tzinfo=UTC)

    return UserProfile(
        id=model.id,
        name=model.name,
        activity_type=ActivityType(model.activity_type),
        skill_level=SkillLevel.from_string(model.skill_level),
        avg_speed_kmh=model.avg_speed_kmh,
        max_distance_km=model.max_distance_km,
        preferred_terrain=TerrainType(model.preferred_terrain)
        if model.preferred_terrain
        else None,
        preferred_direction=Direction.from_angle(
            _direction_to_angle(model.preferred_direction)
        ),
        home_coordinates=home_coords,
        created_at=created_at,
    )


def _direction_to_angle(direction_str: str) -> int | None:
    """Convert a direction string to an angle (or None for ANY)."""
    for d in Direction:
        if d.value == direction_str:
            return d.angle
    return None


def _route_to_model(route: Route) -> RouteModel:
    """Convert a domain Route to an ORM RouteModel.

    Waypoints are stored as JSON: list of ``[lat, lon]`` pairs.
    """
    waypoints_json: list[list[float]] | None = None
    if route.waypoints:
        waypoints_json = [[wp.latitude, wp.longitude] for wp in route.waypoints]

    return RouteModel(
        id=route.id,
        name=route.name,
        activity_type=route.activity_type.value,
        distance_km=route.distance_km,
        elevation_gain_m=route.elevation_gain_m,
        estimated_duration_min=route.estimated_duration_min,
        difficulty=route.difficulty.value,
        waypoints_json=waypoints_json,
        polyline=route.polyline,
        created_at=route.created_at,
    )


def _model_to_route(model: RouteModel) -> Route:
    """Convert an ORM RouteModel back to a domain Route."""
    waypoints: list[Coordinates] = []
    if model.waypoints_json:
        waypoints = [
            Coordinates(latitude=lat, longitude=lon)
            for lat, lon in model.waypoints_json
        ]

    created_at = model.created_at
    # SQLite doesn't store timezone; assume UTC if missing
    if created_at.tzinfo is None:

        created_at = created_at.replace(tzinfo=UTC)

    return Route(
        id=model.id,
        name=model.name,
        activity_type=ActivityType(model.activity_type),
        distance_km=model.distance_km,
        elevation_gain_m=model.elevation_gain_m,
        estimated_duration_min=int(model.estimated_duration_min),
        difficulty=DifficultyLevel(model.difficulty),
        waypoints=waypoints,
        polyline=model.polyline,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
#  SQL UserProfile Repository
# ---------------------------------------------------------------------------


class SqlUserProfileRepository(UserProfileRepository):
    """SQLAlchemy-backed implementation of UserProfileRepository."""

    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_maker = session_maker

    async def save(self, profile: UserProfile) -> None:
        async with self._session_maker() as session:
            model = _profile_to_model(profile)
            await session.merge(model)
            await session.commit()

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        async with self._session_maker() as session:
            result = await session.execute(
                select(UserProfileModel).where(
                    UserProfileModel.id == profile_id
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_profile(model)

    async def delete(self, profile_id: UUID) -> None:
        async with self._session_maker() as session:
            result = await session.execute(
                select(UserProfileModel).where(
                    UserProfileModel.id == profile_id
                )
            )
            model = result.scalar_one_or_none()
            if model is not None:
                await session.delete(model)
                await session.commit()


# ---------------------------------------------------------------------------
#  SQL Route Repository
# ---------------------------------------------------------------------------


class SqlRouteRepository(RouteRepository):
    """SQLAlchemy-backed implementation of RouteRepository."""

    def __init__(
        self, session_maker: async_sessionmaker[AsyncSession]
    ) -> None:
        self._session_maker = session_maker

    async def save(self, route: Route) -> None:
        async with self._session_maker() as session:
            model = _route_to_model(route)
            await session.merge(model)
            await session.commit()

    async def get_by_id(self, route_id: UUID) -> Route | None:
        async with self._session_maker() as session:
            result = await session.execute(
                select(RouteModel).where(RouteModel.id == route_id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return _model_to_route(model)
