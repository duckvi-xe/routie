"""Abstract base class for route providers.

This is kept as a simple ABC alias so that all route providers
implement the port interface from the use_cases layer.
"""

from __future__ import annotations

from abc import ABC

from routie.use_cases.plan_route import RouteProvider as RouteProviderPort


class RouteProvider(RouteProviderPort, ABC):
    """Abstract route provider marker.

    Implementations must define ``plan_route`` (enforced by the port).
    """
