"""PlanRouteUseCase — orchestrates route planning for a user profile."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from routie.domain.enums import ActivityType, Direction, TerrainType
from routie.domain.models import Route, RoutePlanRequest
from routie.domain.value_objects import Coordinates
from routie.use_cases.manage_profile import (
    ProfileNotFoundError,
    UserProfileRepository,
)


class RouteRepository:
    """Port (interface) for route persistence."""

    async def save(self, route: Route) -> None:
        raise NotImplementedError

    async def get_by_id(self, route_id: UUID) -> Route | None:
        raise NotImplementedError


class RouteProvider:
    """Port (interface) for external route planning services."""

    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: "UserProfile",  # noqa: F821
    ) -> Route:
        raise NotImplementedError


@dataclass(frozen=True)
class PlanRouteRequest:
    """Input data for planning a route."""

    profile_id: UUID
    activity_type: ActivityType
    max_distance_km: float | None = None
    max_duration_min: int | None = None
    preferred_direction: Direction | None = None
    terrain_type: TerrainType | None = None
    start_coordinates: Coordinates | None = None


class PlanRouteUseCase:
    """Application use case for planning a route based on user profile."""

    def __init__(
        self,
        profile_repo: UserProfileRepository,
        route_repo: RouteRepository,
        route_provider: RouteProvider,
    ) -> None:
        self._profile_repo = profile_repo
        self._route_repo = route_repo
        self._route_provider = route_provider

    async def execute(self, request: PlanRouteRequest) -> Route:
        profile = await self._profile_repo.get_by_id(request.profile_id)
        if profile is None:
            raise ProfileNotFoundError(
                f"Profile {request.profile_id} not found"
            )

        domain_request = RoutePlanRequest(
            activity_type=request.activity_type,
            max_distance_km=request.max_distance_km,
            max_duration_min=request.max_duration_min,
            preferred_direction=request.preferred_direction,
            terrain_type=request.terrain_type,
            start_coordinates=request.start_coordinates,
        )

        route = await self._route_provider.plan_route(domain_request, profile)
        await self._route_repo.save(route)
        return route

    async def get_route(self, route_id: UUID) -> Route:
        """Retrieve a persisted route by ID."""
        route = await self._route_repo.get_by_id(route_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        return route


class RouteNotFoundError(Exception):
    """Raised when a requested route does not exist."""
