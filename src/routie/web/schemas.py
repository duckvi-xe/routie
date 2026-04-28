"""Pydantic schemas for API request/response serialization."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
#  Profile schemas
# ---------------------------------------------------------------------------


class CreateProfileRequest(BaseModel):
    """Request body for POST /api/v1/profiles."""

    name: str = Field(..., min_length=1, max_length=100)
    activity_type: str = Field(..., pattern=r"^(running|cycling)$")
    skill_level: str = Field(default="beginner", pattern=r"^(beginner|intermediate|advanced)$")
    avg_speed_kmh: float | None = Field(default=None, ge=0)
    max_distance_km: float | None = Field(default=None, ge=0)
    preferred_terrain: str | None = Field(
        default=None, pattern=r"^(flat|hilly|mixed)$"
    )
    preferred_direction: str | None = Field(
        default=None, pattern=r"^(N|NE|E|SE|S|SW|W|NW|ANY)$"
    )
    home_latitude: float | None = Field(default=None, ge=-90, le=90)
    home_longitude: float | None = Field(default=None, ge=-180, le=180)


class UpdateProfileRequest(BaseModel):
    """Request body for PATCH /api/v1/profiles/{id}."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    skill_level: str | None = Field(
        default=None, pattern=r"^(beginner|intermediate|advanced)$"
    )
    avg_speed_kmh: float | None = Field(default=None, ge=0)
    max_distance_km: float | None = Field(default=None, ge=0)
    preferred_terrain: str | None = Field(
        default=None, pattern=r"^(flat|hilly|mixed)$"
    )
    preferred_direction: str | None = Field(
        default=None, pattern=r"^(N|NE|E|SE|S|SW|W|NW|ANY)$"
    )
    home_latitude: float | None = Field(default=None, ge=-90, le=90)
    home_longitude: float | None = Field(default=None, ge=-180, le=180)


class ProfileResponse(BaseModel):
    """Response body for profile endpoints."""

    id: str
    name: str
    activity_type: str
    skill_level: str
    avg_speed_kmh: float
    max_distance_km: float | None
    preferred_terrain: str | None
    preferred_direction: str
    home_latitude: float | None
    home_longitude: float | None
    created_at: str


# ---------------------------------------------------------------------------
#  Route schemas
# ---------------------------------------------------------------------------


class PlanRouteRequest(BaseModel):
    """Request body for POST /api/v1/routes/plan."""

    profile_id: str
    activity_type: str = Field(..., pattern=r"^(running|cycling)$")
    max_distance_km: float | None = Field(default=None, ge=0)
    max_duration_min: int | None = Field(default=None, ge=0)
    preferred_direction: str | None = Field(
        default=None, pattern=r"^(N|NE|E|SE|S|SW|W|NW|ANY)$"
    )
    terrain_type: str | None = Field(
        default=None, pattern=r"^(flat|hilly|mixed)$"
    )
    start_latitude: float | None = Field(default=None, ge=-90, le=90)
    start_longitude: float | None = Field(default=None, ge=-180, le=180)


class CoordinateSchema(BaseModel):
    """Coordinate pair in a route."""

    latitude: float
    longitude: float


class RouteResponse(BaseModel):
    """Response body for route endpoints."""

    id: str
    name: str
    activity_type: str
    distance_km: float
    elevation_gain_m: float
    estimated_duration_min: int
    difficulty: str
    waypoints: list[CoordinateSchema]
    polyline: str | None
    created_at: str


# ---------------------------------------------------------------------------
#  Error schema
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict = Field(default_factory=lambda: {"code": "UNKNOWN", "message": ""})


# ---------------------------------------------------------------------------
#  Health schema
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
