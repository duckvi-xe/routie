"""Tests for domain models (entities)."""

from uuid import UUID

import pytest

from routie.domain.enums import (
    ActivityType,
    DifficultyLevel,
    Direction,
    SkillLevel,
    TerrainType,
)
from routie.domain.models import Route, RoutePlanRequest, UserProfile
from routie.domain.value_objects import Coordinates


class TestUserProfile:
    def test_create_minimal_profile(self):
        profile = UserProfile.new(name="Runner1", activity_type=ActivityType.RUNNING)
        assert profile.name == "Runner1"
        assert profile.activity_type == ActivityType.RUNNING
        assert profile.skill_level == SkillLevel.BEGINNER
        assert profile.avg_speed_kmh == SkillLevel.BEGINNER.default_speed_kmh
        assert profile.max_distance_km is None
        assert profile.preferred_terrain is None
        assert profile.preferred_direction is Direction.ANY
        assert isinstance(profile.id, UUID)

    def test_create_full_profile(self):
        home = Coordinates(latitude=45.0, longitude=9.0)
        profile = UserProfile.new(
            name="Runner2",
            activity_type=ActivityType.CYCLING,
            skill_level=SkillLevel.ADVANCED,
            avg_speed_kmh=25.0,
            max_distance_km=100.0,
            preferred_terrain=TerrainType.HILLY,
            preferred_direction=Direction.S,
            home_coordinates=home,
        )
        assert profile.avg_speed_kmh == 25.0
        assert profile.max_distance_km == 100.0
        assert profile.home_coordinates == home

    def test_avg_speed_derived_from_skill_if_not_set(self):
        profile = UserProfile.new(
            name="Test",
            activity_type=ActivityType.RUNNING,
            skill_level=SkillLevel.INTERMEDIATE,
        )
        assert profile.avg_speed_kmh == SkillLevel.INTERMEDIATE.default_speed_kmh

    def test_avg_speed_override(self):
        profile = UserProfile.new(
            name="Test",
            activity_type=ActivityType.RUNNING,
            skill_level=SkillLevel.BEGINNER,
            avg_speed_kmh=6.0,
        )
        assert profile.avg_speed_kmh == 6.0

    def test_update_speed(self):
        profile = UserProfile.new(name="Test", activity_type=ActivityType.RUNNING)
        updated = profile.with_speed(10.0)
        assert updated.avg_speed_kmh == 10.0
        assert profile.avg_speed_kmh == 8.0  # original unchanged (immutable)

    def test_update_skill(self):
        profile = UserProfile.new(
            name="Test",
            activity_type=ActivityType.RUNNING,
            skill_level=SkillLevel.BEGINNER,
        )
        updated = profile.with_skill(SkillLevel.ADVANCED)
        assert updated.skill_level == SkillLevel.ADVANCED
        # avg_speed_kmh should update to the new skill default
        assert updated.avg_speed_kmh == SkillLevel.ADVANCED.default_speed_kmh

    def test_update_preferences(self):
        profile = UserProfile.new(name="Test", activity_type=ActivityType.RUNNING)
        updated = profile.with_preferences(
            max_distance_km=42.0,
            preferred_terrain=TerrainType.FLAT,
            preferred_direction=Direction.N,
        )
        assert updated.max_distance_km == 42.0
        assert updated.preferred_terrain == TerrainType.FLAT
        assert updated.preferred_direction == Direction.N

    def test_id_is_unique(self):
        a = UserProfile.new(name="A", activity_type=ActivityType.RUNNING)
        b = UserProfile.new(name="B", activity_type=ActivityType.CYCLING)
        assert a.id != b.id

    def test_immutable_id(self):
        profile = UserProfile.new(name="Test", activity_type=ActivityType.RUNNING)
        with pytest.raises(AttributeError):
            profile.name = "Changed"


class TestRoutePlanRequest:
    def test_create_minimal_request(self):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        assert req.activity_type == ActivityType.RUNNING
        assert req.max_distance_km is None
        assert req.max_duration_min is None
        assert req.preferred_direction is None
        assert req.terrain_type is None
        assert req.start_coordinates is None

    def test_create_full_request(self):
        start = Coordinates(latitude=45.0, longitude=9.0)
        req = RoutePlanRequest(
            activity_type=ActivityType.CYCLING,
            max_distance_km=50.0,
            max_duration_min=120,
            preferred_direction=Direction.SE,
            terrain_type=TerrainType.HILLY,
            start_coordinates=start,
        )
        assert req.max_distance_km == 50.0
        assert req.max_duration_min == 120
        assert req.preferred_direction == Direction.SE

    def test_immutable_by_default(self):
        req = RoutePlanRequest(activity_type=ActivityType.RUNNING)
        with pytest.raises(AttributeError):
            req.activity_type = ActivityType.CYCLING

    def test_negative_distance_raises_error(self):
        with pytest.raises(ValueError, match="max_distance_km must be non-negative"):
            RoutePlanRequest(activity_type=ActivityType.RUNNING, max_distance_km=-10.0)

    def test_negative_duration_raises_error(self):
        with pytest.raises(ValueError, match="max_duration_min must be non-negative"):
            RoutePlanRequest(
                activity_type=ActivityType.RUNNING, max_duration_min=-30
            )


class TestRoute:
    def test_create_minimal_route(self):
        route = Route.new(
            name="Morning Run",
            activity_type=ActivityType.RUNNING,
            distance_km=10.0,
            elevation_gain_m=50.0,
            estimated_duration_min=60,
        )
        assert route.name == "Morning Run"
        assert route.activity_type == ActivityType.RUNNING
        assert route.distance_km == 10.0
        assert route.elevation_gain_m == 50.0
        assert route.estimated_duration_min == 60
        assert route.difficulty == DifficultyLevel.EASY
        assert isinstance(route.id, UUID)
        assert route.created_at is not None

    def test_difficulty_calculation_easy(self):
        route = Route.new(
            name="Easy Walk",
            activity_type=ActivityType.RUNNING,
            distance_km=5.0,
            elevation_gain_m=20.0,
            estimated_duration_min=30,
        )
        assert route.difficulty == DifficultyLevel.EASY

    def test_difficulty_calculation_moderate(self):
        route = Route.new(
            name="Moderate Run",
            activity_type=ActivityType.RUNNING,
            distance_km=15.0,
            elevation_gain_m=200.0,
            estimated_duration_min=90,
        )
        assert route.difficulty == DifficultyLevel.MODERATE

    def test_difficulty_calculation_hard(self):
        route = Route.new(
            name="Hard Trail",
            activity_type=ActivityType.RUNNING,
            distance_km=30.0,
            elevation_gain_m=800.0,
            estimated_duration_min=180,
        )
        assert route.difficulty == DifficultyLevel.HARD

    def test_difficulty_for_cycling_is_based_on_distance(self):
        route = Route.new(
            name="Long Ride",
            activity_type=ActivityType.CYCLING,
            distance_km=80.0,
            elevation_gain_m=300.0,
            estimated_duration_min=240,
        )
        assert route.difficulty == DifficultyLevel.MODERATE

    def test_route_with_waypoints(self):
        wp = [
            Coordinates(latitude=45.0, longitude=9.0),
            Coordinates(latitude=45.1, longitude=9.1),
        ]
        route = Route.new(
            name="Point to Point",
            activity_type=ActivityType.RUNNING,
            distance_km=5.0,
            elevation_gain_m=0.0,
            estimated_duration_min=30,
            waypoints=wp,
        )
        assert len(route.waypoints) == 2
        assert route.waypoints[0] == wp[0]

    def test_route_without_waypoints_defaults_to_empty(self):
        route = Route.new(
            name="No Waypoints",
            activity_type=ActivityType.RUNNING,
            distance_km=5.0,
            elevation_gain_m=0.0,
            estimated_duration_min=30,
        )
        assert route.waypoints == []

    def test_immutable_entity(self):
        route = Route.new(
            name="Test",
            activity_type=ActivityType.RUNNING,
            distance_km=5.0,
            elevation_gain_m=0.0,
            estimated_duration_min=30,
        )
        with pytest.raises(AttributeError):
            route.name = "Changed"
