"""Tests for polyline encoding/decoding utilities."""

from __future__ import annotations

import polyline

from routie.domain.value_objects import Coordinates
from routie.service.providers.polyline import decode_polyline, encode_polyline


class TestPolylineRoundtrip:
    """Verify that encode → decode returns approximately the original coordinates."""

    def test_roundtrip_two_points(self):
        coords = [
            Coordinates(latitude=45.4642, longitude=9.1900),
            Coordinates(latitude=45.4742, longitude=9.2000),
        ]
        encoded = encode_polyline(coords)
        decoded = decode_polyline(encoded)

        assert len(decoded) == len(coords)
        for orig, dec in zip(coords, decoded, strict=True):
            assert abs(orig.latitude - dec[0]) < 0.00001
            assert abs(orig.longitude - dec[1]) < 0.00001

    def test_roundtrip_multiple_points(self):
        coords = [
            Coordinates(latitude=41.9028, longitude=12.4964),
            Coordinates(latitude=41.9128, longitude=12.5064),
            Coordinates(latitude=41.9228, longitude=12.5164),
            Coordinates(latitude=41.9328, longitude=12.5264),
            Coordinates(latitude=41.9428, longitude=12.5364),
        ]
        encoded = encode_polyline(coords)
        decoded = decode_polyline(encoded)

        assert len(decoded) == len(coords)
        for orig, dec in zip(coords, decoded, strict=True):
            assert abs(orig.latitude - dec[0]) < 0.00001
            assert abs(orig.longitude - dec[1]) < 0.00001

    def test_roundtrip_empty_list(self):
        assert encode_polyline([]) == ""
        assert decode_polyline("") == []

    def test_roundtrip_single_point(self):
        coords = [Coordinates(latitude=41.9028, longitude=12.4964)]
        encoded = encode_polyline(coords)
        decoded = decode_polyline(encoded)
        assert len(decoded) == 1
        assert abs(decoded[0][0] - 41.9028) < 0.00001
        assert abs(decoded[0][1] - 12.4964) < 0.00001

    def test_polyline_library_encode_direct(self):
        """Verify the underlying library works as expected."""
        pairs = [(45.4642, 9.1900), (45.4742, 9.2000)]
        encoded = polyline.encode(pairs)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_polyline_library_decode_direct(self):
        """Verify the underlying library decode works."""
        encoded = polyline.encode([(45.4642, 9.1900)])
        decoded = polyline.decode(encoded)
        assert isinstance(decoded, list)
        assert len(decoded) == 1
