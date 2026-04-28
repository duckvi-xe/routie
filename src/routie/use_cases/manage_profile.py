"""ManageProfileUseCase — create, read, update, delete user profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from routie.domain.enums import (
    ActivityType,
    Direction,
    SkillLevel,
    TerrainType,
)
from routie.domain.models import UserProfile
from routie.domain.value_objects import Coordinates


class ProfileNotFoundError(Exception):
    """Raised when a requested profile does not exist."""


@dataclass(frozen=True)
class CreateProfileRequest:
    """Input data for creating a new profile."""

    name: str
    activity_type: ActivityType
    skill_level: SkillLevel = SkillLevel.BEGINNER
    avg_speed_kmh: float | None = None
    max_distance_km: float | None = None
    preferred_terrain: TerrainType | None = None
    preferred_direction: Direction = Direction.ANY
    home_coordinates: Coordinates | None = None


@dataclass(frozen=True)
class UpdateProfileRequest:
    """Input data for updating an existing profile.

    Fields set to None are left unchanged.
    """

    profile_id: UUID
    name: str | None = None
    skill_level: SkillLevel | None = None
    avg_speed_kmh: float | None = None
    max_distance_km: float | None = None
    preferred_terrain: TerrainType | None = None
    preferred_direction: Direction | None = None
    home_coordinates: Coordinates | None = field(default=None, compare=False)


class UserProfileRepository:
    """Port (interface) for user profile persistence."""

    async def save(self, profile: UserProfile) -> None:
        raise NotImplementedError

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        raise NotImplementedError

    async def delete(self, profile_id: UUID) -> None:
        raise NotImplementedError


class ManageProfileUseCase:
    """Application use case for CRUD operations on user profiles."""

    def __init__(self, profile_repo: UserProfileRepository) -> None:
        self._repo = profile_repo

    async def create(self, request: CreateProfileRequest) -> UserProfile:
        profile = UserProfile.new(
            name=request.name,
            activity_type=request.activity_type,
            skill_level=request.skill_level,
            avg_speed_kmh=request.avg_speed_kmh,
            max_distance_km=request.max_distance_km,
            preferred_terrain=request.preferred_terrain,
            preferred_direction=request.preferred_direction,
            home_coordinates=request.home_coordinates,
        )
        await self._repo.save(profile)
        return profile

    async def get(self, profile_id: UUID) -> UserProfile:
        profile = await self._repo.get_by_id(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile {profile_id} not found")
        return profile

    async def update(self, request: UpdateProfileRequest) -> UserProfile:
        profile = await self._repo.get_by_id(request.profile_id)
        if profile is None:
            raise ProfileNotFoundError(
                f"Profile {request.profile_id} not found"
            )

        updated = profile
        if request.name is not None:
            updated = UserProfile(
                id=updated.id,
                name=request.name,
                activity_type=updated.activity_type,
                skill_level=updated.skill_level,
                avg_speed_kmh=updated.avg_speed_kmh,
                max_distance_km=updated.max_distance_km,
                preferred_terrain=updated.preferred_terrain,
                preferred_direction=updated.preferred_direction,
                home_coordinates=updated.home_coordinates,
                created_at=updated.created_at,
            )
        if request.skill_level is not None:
            updated = updated.with_skill(request.skill_level)
        if request.avg_speed_kmh is not None:
            updated = updated.with_speed(request.avg_speed_kmh)
        if request.max_distance_km is not None or request.preferred_terrain is not None or request.preferred_direction is not None:
            updated = updated.with_preferences(
                max_distance_km=request.max_distance_km,
                preferred_terrain=request.preferred_terrain,
                preferred_direction=request.preferred_direction,
            )
        if request.home_coordinates is not None:
            # home_coordinates not handled by with_preferences, do it directly
            updated = UserProfile(
                id=updated.id,
                name=updated.name,
                activity_type=updated.activity_type,
                skill_level=updated.skill_level,
                avg_speed_kmh=updated.avg_speed_kmh,
                max_distance_km=updated.max_distance_km,
                preferred_terrain=updated.preferred_terrain,
                preferred_direction=updated.preferred_direction,
                home_coordinates=request.home_coordinates,
                created_at=updated.created_at,
            )

        await self._repo.save(updated)
        return updated

    async def delete(self, profile_id: UUID) -> None:
        profile = await self._repo.get_by_id(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Profile {profile_id} not found")
        await self._repo.delete(profile_id)
