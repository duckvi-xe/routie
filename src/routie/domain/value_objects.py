"""Domain value objects for Routie."""

from __future__ import annotations

import math
from dataclasses import dataclass


EARTH_RADIUS_KM = 6371.0


class InvalidCoordinateError(ValueError):
    """Raised when coordinates are out of valid range."""


@dataclass(frozen=True)
class Coordinates:
    """Immutable geographical coordinates (latitude, longitude) in decimal degrees."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise InvalidCoordinateError(
                f"Latitude must be between -90 and 90, got {self.latitude}"
            )
        if not (-180.0 <= self.longitude <= 180.0):
            raise InvalidCoordinateError(
                f"Longitude must be between -180 and 180, got {self.longitude}"
            )

    def distance_to(self, other: Coordinates) -> float:
        """Haversine distance in km to another coordinate."""
        lat1, lon1 = math.radians(self.latitude), math.radians(self.longitude)
        lat2, lon2 = math.radians(other.latitude), math.radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))
        return EARTH_RADIUS_KM * c

    def to_tuple(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)


@dataclass(frozen=True)
class Distance:
    """Non-negative distance value, stored in km."""

    _km: float

    @classmethod
    def from_km(cls, value: float) -> Distance:
        if value < 0:
            raise ValueError(f"Distance must be non-negative, got {value}")
        return cls(_km=value)

    @classmethod
    def from_meters(cls, value: float) -> Distance:
        if value < 0:
            raise ValueError(f"Distance must be non-negative, got {value}")
        return cls(_km=value / 1000.0)

    @property
    def km(self) -> float:
        return self._km

    @property
    def meters(self) -> float:
        return self._km * 1000.0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Distance):
            return NotImplemented
        return math.isclose(self._km, other._km, rel_tol=1e-9)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Distance):
            return NotImplemented
        return self._km < other._km

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Distance):
            return NotImplemented
        return self._km <= other._km

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Distance):
            return NotImplemented
        return self._km > other._km

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Distance):
            return NotImplemented
        return self._km >= other._km

    def __hash__(self) -> int:
        return hash(round(self._km, 6))

    def __repr__(self) -> str:
        return f"Distance({self._km:.2f} km)"


@dataclass(frozen=True)
class Duration:
    """Non-negative duration, stored in minutes."""

    _minutes: int

    @classmethod
    def from_minutes(cls, value: int) -> Duration:
        if value < 0:
            raise ValueError(f"Duration must be non-negative, got {value}")
        return cls(_minutes=value)

    @property
    def minutes(self) -> int:
        return self._minutes

    @property
    def hours(self) -> float:
        return self._minutes / 60.0

    @property
    def formatted(self) -> str:
        h = self._minutes // 60
        m = self._minutes % 60
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self._minutes == other._minutes

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self._minutes < other._minutes

    def __le__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self._minutes <= other._minutes

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self._minutes > other._minutes

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, Duration):
            return NotImplemented
        return self._minutes >= other._minutes

    def __hash__(self) -> int:
        return hash(self._minutes)

    def __repr__(self) -> str:
        return f"Duration({self._minutes} min)"
