"""Tests for domain enums."""

from routie.domain.enums import (
    ActivityType,
    ActivityTypeError,
    DifficultyLevel,
    Direction,
    SkillLevel,
    SkillLevelError,
    TerrainType,
)


class TestActivityType:
    def test_has_running_and_cycling(self):
        assert ActivityType.RUNNING.value == "running"
        assert ActivityType.CYCLING.value == "cycling"

    def test_contains_all_expected(self):
        values = {e.value for e in ActivityType}
        assert values == {"running", "cycling"}


class TestSkillLevel:
    def test_has_three_levels(self):
        assert SkillLevel.BEGINNER.value == "beginner"
        assert SkillLevel.INTERMEDIATE.value == "intermediate"
        assert SkillLevel.ADVANCED.value == "advanced"

    def test_beginner_default_speed(self):
        assert SkillLevel.BEGINNER.default_speed_kmh == 8.0

    def test_intermediate_default_speed(self):
        assert SkillLevel.INTERMEDIATE.default_speed_kmh == 12.0

    def test_advanced_default_speed(self):
        assert SkillLevel.ADVANCED.default_speed_kmh == 16.0

    def test_default_speed_is_positive(self):
        for level in SkillLevel:
            assert level.default_speed_kmh > 0

    def test_level_hierarchy(self):
        assert SkillLevel.ADVANCED > SkillLevel.INTERMEDIATE
        assert SkillLevel.INTERMEDIATE > SkillLevel.BEGINNER


class TestTerrainType:
    def test_has_three_terrains(self):
        assert TerrainType.FLAT.value == "flat"
        assert TerrainType.HILLY.value == "hilly"
        assert TerrainType.MIXED.value == "mixed"

    def test_terrain_elevation_factor(self):
        assert TerrainType.FLAT.elevation_factor == 1.0
        assert TerrainType.HILLY.elevation_factor == 3.0
        assert TerrainType.MIXED.elevation_factor == 2.0


class TestDirection:
    def test_has_cardinal_and_intercardinal(self):
        assert Direction.N.value == "N"
        assert Direction.NE.value == "NE"
        assert Direction.E.value == "E"
        assert Direction.SE.value == "SE"
        assert Direction.S.value == "S"
        assert Direction.SW.value == "SW"
        assert Direction.W.value == "W"
        assert Direction.NW.value == "NW"
        assert Direction.ANY.value == "ANY"

    def test_angle_in_degrees(self):
        assert Direction.N.angle == 0
        assert Direction.E.angle == 90
        assert Direction.S.angle == 180
        assert Direction.W.angle == 270
        assert Direction.NE.angle == 45
        assert Direction.SE.angle == 135
        assert Direction.SW.angle == 225
        assert Direction.NW.angle == 315

    def test_any_direction_has_no_angle(self):
        assert Direction.ANY.angle is None

    def test_from_angle_returns_correct_direction(self):
        assert Direction.from_angle(0) == Direction.N
        assert Direction.from_angle(90) == Direction.E
        assert Direction.from_angle(180) == Direction.S
        assert Direction.from_angle(270) == Direction.W
        assert Direction.from_angle(45) == Direction.NE
        assert Direction.from_angle(135) == Direction.SE
        assert Direction.from_angle(225) == Direction.SW
        assert Direction.from_angle(315) == Direction.NW

    def test_from_angle_normalizes_negative(self):
        assert Direction.from_angle(-90) == Direction.W

    def test_from_angle_normalizes_over_360(self):
        assert Direction.from_angle(450) == Direction.E

    def test_from_angle_returns_any_for_none(self):
        assert Direction.from_angle(None) == Direction.ANY


class TestDifficultyLevel:
    def test_has_three_levels(self):
        assert DifficultyLevel.EASY.value == "easy"
        assert DifficultyLevel.MODERATE.value == "moderate"
        assert DifficultyLevel.HARD.value == "hard"

    def test_comparison_operators(self):
        assert DifficultyLevel.EASY < DifficultyLevel.MODERATE
        assert DifficultyLevel.MODERATE < DifficultyLevel.HARD
        assert DifficultyLevel.HARD > DifficultyLevel.EASY


class TestActivityTypeError:
    def test_is_exception(self):
        exc = ActivityTypeError("invalid activity type")
        assert isinstance(exc, ValueError)
        assert str(exc) == "invalid activity type"


class TestSkillLevelError:
    def test_is_exception(self):
        exc = SkillLevelError("invalid skill level")
        assert isinstance(exc, ValueError)
        assert str(exc) == "invalid skill level"
