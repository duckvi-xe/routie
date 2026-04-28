"""Domain enums for Routie."""

from __future__ import annotations

from enum import Enum


class ActivityType(str, Enum):
    """Type of physical activity."""

    RUNNING = "running"
    CYCLING = "cycling"


class SkillLevel(Enum):
    """User skill level with associated default average speed (km/h)."""

    BEGINNER = ("beginner", 8.0)
    INTERMEDIATE = ("intermediate", 12.0)
    ADVANCED = ("advanced", 16.0)

    def __init__(self, label: str, speed_kmh: float) -> None:
        self._label = label
        self._speed_kmh = speed_kmh

    @property
    def default_speed_kmh(self) -> float:
        return self._speed_kmh

    @property
    def value(self) -> str:
        return self._label

    @classmethod
    def from_string(cls, label: str) -> "SkillLevel":
        """Return a SkillLevel from its string label."""
        for level in cls:
            if level.value == label:
                return level
        raise SkillLevelError(f"Unknown skill level: {label}")

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, SkillLevel):
            return NotImplemented
        levels = [SkillLevel.BEGINNER, SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED]
        return levels.index(self) > levels.index(other)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SkillLevel):
            return NotImplemented
        return other.__gt__(self)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, SkillLevel):
            return NotImplemented
        return self == other or self > other

    def __le__(self, other: object) -> bool:
        if not isinstance(other, SkillLevel):
            return NotImplemented
        return self == other or self < other


# Elevation factor per terrain type
_TERRAIN_FACTORS: dict[str, float] = {
    "flat": 1.0,
    "hilly": 3.0,
    "mixed": 2.0,
}


class TerrainType(str, Enum):
    """Type of terrain with elevation factor."""

    FLAT = "flat"
    HILLY = "hilly"
    MIXED = "mixed"

    @property
    def elevation_factor(self) -> float:
        return _TERRAIN_FACTORS[self.value]


class Direction(Enum):
    """Compass direction or ANY for unconstrained."""

    N = ("N", 0)
    NE = ("NE", 45)
    E = ("E", 90)
    SE = ("SE", 135)
    S = ("S", 180)
    SW = ("SW", 225)
    W = ("W", 270)
    NW = ("NW", 315)
    ANY = ("ANY", None)

    def __init__(self, label: str, angle: int | None) -> None:
        self._label = label
        self._angle = angle

    @property
    def angle(self) -> int | None:
        return self._angle

    @property
    def value(self) -> str:
        return self._label

    @classmethod
    def from_angle(cls, degrees: int | None) -> Direction:
        """Return the closest Direction for a given angle in degrees."""
        if degrees is None:
            return cls.ANY
        normalized = degrees % 360
        for d in cls:
            if d.angle == normalized:
                return d
        closest = min(
            (d for d in cls if d.angle is not None),
            key=lambda d: abs(d.angle - normalized),
        )
        return closest


class DifficultyLevel(str, Enum):
    """Route difficulty level."""

    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, DifficultyLevel):
            return NotImplemented
        levels = [DifficultyLevel.EASY, DifficultyLevel.MODERATE, DifficultyLevel.HARD]
        return levels.index(self) < levels.index(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, DifficultyLevel):
            return NotImplemented
        return other.__lt__(self)

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, DifficultyLevel):
            return NotImplemented
        return self == other or self > other

    def __le__(self, other: object) -> bool:
        if not isinstance(other, DifficultyLevel):
            return NotImplemented
        return self == other or self < other


class ActivityTypeError(ValueError):
    """Raised when an invalid activity type is provided."""


class SkillLevelError(ValueError):
    """Raised when an invalid skill level is provided."""
