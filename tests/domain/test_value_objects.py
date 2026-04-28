"""Tests for domain value objects."""

import math

import pytest

from routie.domain.value_objects import (
    Coordinates,
    Distance,
    Duration,
    InvalidCoordinateError,
)


class TestCoordinates:
    def test_valid_coordinates(self):
        coords = Coordinates(latitude=45.0, longitude=9.0)
        assert coords.latitude == 45.0
        assert coords.longitude == 9.0

    def test_latitude_ranges(self):
        assert Coordinates(latitude=90.0, longitude=0.0)
        assert Coordinates(latitude=-90.0, longitude=0.0)

    def test_longitude_ranges(self):
        assert Coordinates(latitude=0.0, longitude=180.0)
        assert Coordinates(latitude=0.0, longitude=-180.0)

    @pytest.mark.parametrize("lat", [91.0, -91.0, 100, -100])
    def test_invalid_latitude_raises_error(self, lat):
        with pytest.raises(InvalidCoordinateError, match="Latitude must be between -90 and 90"):
            Coordinates(latitude=lat, longitude=0.0)

    @pytest.mark.parametrize("lon", [181.0, -181.0, 200, -200])
    def test_invalid_longitude_raises_error(self, lon):
        with pytest.raises(InvalidCoordinateError, match="Longitude must be between -180 and 180"):
            Coordinates(latitude=0.0, longitude=lon)

    def test_immutable(self):
        coords = Coordinates(latitude=45.0, longitude=9.0)
        with pytest.raises(AttributeError):
            coords.latitude = 50.0

    def test_equality(self):
        a = Coordinates(latitude=45.0, longitude=9.0)
        b = Coordinates(latitude=45.0, longitude=9.0)
        c = Coordinates(latitude=46.0, longitude=9.0)
        assert a == b
        assert a != c

    def test_hashable(self):
        a = Coordinates(latitude=45.0, longitude=9.0)
        b = Coordinates(latitude=45.0, longitude=9.0)
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_repr(self):
        coords = Coordinates(latitude=45.5, longitude=9.2)
        assert "45.5" in repr(coords)
        assert "9.2" in repr(coords)

    def test_distance_to_self_is_zero(self):
        coords = Coordinates(latitude=45.0, longitude=9.0)
        assert coords.distance_to(coords) == 0.0

    def test_distance_to_known_points(self):
        milan = Coordinates(latitude=45.4642, longitude=9.1900)
        rome = Coordinates(latitude=41.9028, longitude=12.4964)
        distance = milan.distance_to(rome)
        # Milan-Rome is ~475-485 km (Haversine)
        assert 470 <= distance <= 490

    def test_distance_is_commutative(self):
        a = Coordinates(latitude=45.0, longitude=9.0)
        b = Coordinates(latitude=46.0, longitude=11.0)
        assert math.isclose(a.distance_to(b), b.distance_to(a))

    def test_to_tuple(self):
        coords = Coordinates(latitude=45.5, longitude=9.2)
        assert coords.to_tuple() == (45.5, 9.2)


class TestDistance:
    def test_from_km(self):
        d = Distance.from_km(10.0)
        assert d.km == 10.0
        assert d.meters == 10000.0

    def test_from_meters(self):
        d = Distance.from_meters(5000.0)
        assert d.meters == 5000.0
        assert d.km == 5.0

    def test_non_positive_km_raises_error(self):
        with pytest.raises(ValueError, match="Distance must be non-negative"):
            Distance.from_km(-1.0)

    def test_non_positive_meters_raises_error(self):
        with pytest.raises(ValueError, match="Distance must be non-negative"):
            Distance.from_meters(-100.0)

    def test_zero_distance(self):
        d = Distance.from_km(0.0)
        assert d.km == 0.0
        assert d.meters == 0.0

    def test_equality(self):
        a = Distance.from_km(10.0)
        b = Distance.from_meters(10000.0)
        assert a == b

    def test_comparison(self):
        a = Distance.from_km(5.0)
        b = Distance.from_km(10.0)
        assert a < b
        assert b > a
        assert a <= b
        assert b >= a

    def test_comparison_with_equal(self):
        a = Distance.from_km(10.0)
        b = Distance.from_km(10.0)
        assert a <= b
        assert a >= b

    def test_repr(self):
        d = Distance.from_km(10.5)
        assert "10.5" in repr(d)
        assert "km" in repr(d)


class TestDuration:
    def test_from_minutes(self):
        d = Duration.from_minutes(30)
        assert d.minutes == 30

    @pytest.mark.parametrize("mins", [-1, -60])
    def test_non_positive_minutes_raises_error(self, mins):
        with pytest.raises(ValueError, match="Duration must be non-negative"):
            Duration.from_minutes(mins)

    def test_zero_duration(self):
        d = Duration.from_minutes(0)
        assert d.minutes == 0

    def test_hours_property(self):
        d = Duration.from_minutes(90)
        assert d.hours == 1.5

    def test_formatted(self):
        assert Duration.from_minutes(90).formatted == "1h 30m"
        assert Duration.from_minutes(45).formatted == "45m"
        assert Duration.from_minutes(0).formatted == "0m"
        assert Duration.from_minutes(120).formatted == "2h 0m"

    def test_equality(self):
        a = Duration.from_minutes(30)
        b = Duration.from_minutes(30)
        c = Duration.from_minutes(45)
        assert a == b
        assert a != c

    def test_comparison(self):
        a = Duration.from_minutes(15)
        b = Duration.from_minutes(30)
        assert a < b
        assert b > a
        assert a <= b
        assert b >= a

    def test_repr(self):
        d = Duration.from_minutes(30)
        assert "30" in repr(d)
        assert "min" in repr(d)
