"""Abstract base class for route providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from routie.domain.models import Route, RoutePlanRequest, UserProfile


class RouteProvider(ABC):
    """Interface for external route planning services.

    Implementations: MockRouteProvider, GraphHopperProvider, StravaProvider.
    """

    @abstractmethod
    async def plan_route(
        self,
        request: RoutePlanRequest,
        profile: UserProfile,
    ) -> Route:
        """Plan a route matching the given request and user profile."""
