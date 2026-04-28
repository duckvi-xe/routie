"""Polyline encoding/decoding utilities wrapping the polyline library."""

from __future__ import annotations

import polyline

from routie.domain.value_objects import Coordinates


def encode_polyline(waypoints: list[Coordinates]) -> str:
    """Encode a list of Coordinates into a Google polyline string.

    Args:
        waypoints: List of waypoint Coordinates.

    Returns:
        Encoded polyline string. Empty string for empty input.
    """
    if not waypoints:
        return ""
    pairs = [(wp.latitude, wp.longitude) for wp in waypoints]
    return polyline.encode(pairs)


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google polyline string into a list of (lat, lng) tuples.

    Args:
        encoded: Polyline string.

    Returns:
        List of (latitude, longitude) tuples. Empty list for empty input.
    """
    if not encoded:
        return []
    return polyline.decode(encoded)
