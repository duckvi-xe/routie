"""In-memory implementations of repository ports.

These are suitable for development, testing, and small-scale PoC usage.
In production, replace with SQLAlchemy-backed repositories.
"""

from __future__ import annotations

from uuid import UUID

from routie.domain.models import Route, UserProfile
from routie.use_cases.manage_profile import UserProfileRepository
from routie.use_cases.plan_route import RouteRepository


class InMemoryUserProfileRepository(UserProfileRepository):
    """In-memory implementation of UserProfileRepository."""

    def __init__(self) -> None:
        self._profiles: dict[UUID, UserProfile] = {}

    async def save(self, profile: UserProfile) -> None:
        self._profiles[profile.id] = profile

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        return self._profiles.get(profile_id)

    async def delete(self, profile_id: UUID) -> None:
        self._profiles.pop(profile_id, None)


class InMemoryRouteRepository(RouteRepository):
    """In-memory implementation of RouteRepository."""

    def __init__(self) -> None:
        self._routes: dict[UUID, Route] = {}

    async def save(self, route: Route) -> None:
        self._routes[route.id] = route

    async def get_by_id(self, route_id: UUID) -> Route | None:
        return self._routes.get(route_id)
