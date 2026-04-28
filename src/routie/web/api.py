"""FastAPI router for Routie API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from routie.domain.enums import (
    ActivityType,
    Direction,
    SkillLevel,
    SkillLevelError,
    TerrainType,
)
from routie.domain.value_objects import Coordinates
from routie.use_cases.manage_profile import (
    CreateProfileRequest as CreateProfileUCRequest,
)
from routie.use_cases.manage_profile import (
    ManageProfileUseCase,
    ProfileNotFoundError,
)
from routie.use_cases.manage_profile import (
    UpdateProfileRequest as UpdateProfileUCRequest,
)
from routie.use_cases.plan_route import (
    PlanRouteRequest as PlanRouteUCRequest,
)
from routie.use_cases.plan_route import (
    PlanRouteUseCase,
    RouteNotFoundError,
)
from routie.web.schemas import (
    CoordinateSchema,
    CreateProfileRequest,
    ErrorResponse,
    HealthResponse,
    PlanRouteRequest,
    ProfileResponse,
    RouteResponse,
    UpdateProfileRequest,
)


def _build_profile_response(profile) -> ProfileResponse:
    return ProfileResponse(
        id=str(profile.id),
        name=profile.name,
        activity_type=profile.activity_type.value,
        skill_level=profile.skill_level.value,
        avg_speed_kmh=profile.avg_speed_kmh,
        max_distance_km=profile.max_distance_km,
        preferred_terrain=profile.preferred_terrain.value if profile.preferred_terrain else None,
        preferred_direction=profile.preferred_direction.value,
        home_latitude=profile.home_coordinates.latitude if profile.home_coordinates else None,
        home_longitude=profile.home_coordinates.longitude if profile.home_coordinates else None,
        created_at=profile.created_at.isoformat(),
    )


def _build_route_response(route) -> RouteResponse:
    return RouteResponse(
        id=str(route.id),
        name=route.name,
        activity_type=route.activity_type.value,
        distance_km=route.distance_km,
        elevation_gain_m=route.elevation_gain_m,
        estimated_duration_min=route.estimated_duration_min,
        difficulty=route.difficulty.value,
        waypoints=[
            CoordinateSchema(latitude=wp.latitude, longitude=wp.longitude)
            for wp in route.waypoints
        ],
        polyline=route.polyline,
        created_at=route.created_at.isoformat(),
    )


def _parse_activity_type(value: str) -> ActivityType:
    try:
        return ActivityType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error("VALIDATION_ERROR", f"Invalid activity_type: {value}"),
        ) from None


def _parse_skill_level(value: str) -> SkillLevel:
    try:
        return SkillLevel.from_string(value)
    except SkillLevelError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error("VALIDATION_ERROR", f"Invalid skill_level: {value}"),
        ) from None


def _parse_terrain(value: str | None) -> TerrainType | None:
    if value is None:
        return None
    try:
        return TerrainType(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_error("VALIDATION_ERROR", f"Invalid terrain_type: {value}"),
        ) from None


def _parse_direction(value: str | None) -> Direction | None:
    if value is None:
        return None
    for d in Direction:
        if d.value == value:
            return d
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=_error("VALIDATION_ERROR", f"Invalid direction: {value}"),
    )


def _error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def create_router(
    manage_profile_uc: ManageProfileUseCase,
    plan_route_uc: PlanRouteUseCase,
) -> APIRouter:
    """Create the FastAPI router wired with use case instances."""
    router = APIRouter()

    # -----------------------------------------------------------------------
    #  Health
    # -----------------------------------------------------------------------

    @router.get("/health", response_model=HealthResponse)
    async def health():
        return HealthResponse(status="ok", version="0.1.0")

    # -----------------------------------------------------------------------
    #  Profiles
    # -----------------------------------------------------------------------

    @router.post(
        "/profiles",
        response_model=ProfileResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_profile(body: CreateProfileRequest):
        home_coords = None
        if body.home_latitude is not None and body.home_longitude is not None:
            home_coords = Coordinates(
                latitude=body.home_latitude, longitude=body.home_longitude
            )

        domain_req = CreateProfileUCRequest(
            name=body.name,
            activity_type=_parse_activity_type(body.activity_type),
            skill_level=_parse_skill_level(body.skill_level),
            avg_speed_kmh=body.avg_speed_kmh,
            max_distance_km=body.max_distance_km,
            preferred_terrain=_parse_terrain(body.preferred_terrain),
            preferred_direction=_parse_direction(body.preferred_direction)
            or Direction.ANY,
            home_coordinates=home_coords,
        )
        profile = await manage_profile_uc.create(domain_req)
        return _build_profile_response(profile)

    @router.get(
        "/profiles/{profile_id}",
        response_model=ProfileResponse,
        responses={404: {"model": ErrorResponse}},
    )
    async def get_profile(profile_id: str):
        try:
            uid = UUID(profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=_error("VALIDATION_ERROR", f"Invalid UUID: {profile_id}"),
            ) from None
        try:
            profile = await manage_profile_uc.get(uid)
        except ProfileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(
                    "PROFILE_NOT_FOUND", f"Profile {profile_id} not found"
                ),
            ) from None
        return _build_profile_response(profile)

    @router.patch(
        "/profiles/{profile_id}",
        response_model=ProfileResponse,
        responses={404: {"model": ErrorResponse}},
    )
    async def update_profile(profile_id: str, body: UpdateProfileRequest):
        try:
            uid = UUID(profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=_error("VALIDATION_ERROR", f"Invalid UUID: {profile_id}"),
            ) from None

        home_coords = None
        if body.home_latitude is not None or body.home_longitude is not None:
            try:
                existing = await manage_profile_uc.get(uid)
            except ProfileNotFoundError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=_error(
                        "PROFILE_NOT_FOUND", f"Profile {profile_id} not found"
                    ),
                ) from None
            lat = body.home_latitude if body.home_latitude is not None else (
                existing.home_coordinates.latitude
                if existing.home_coordinates
                else 45.0
            )
            lon = body.home_longitude if body.home_longitude is not None else (
                existing.home_coordinates.longitude
                if existing.home_coordinates
                else 9.0
            )
            home_coords = Coordinates(latitude=lat, longitude=lon)

        domain_req = UpdateProfileUCRequest(
            profile_id=uid,
            name=body.name,
            skill_level=_parse_skill_level(body.skill_level)
            if body.skill_level
            else None,
            avg_speed_kmh=body.avg_speed_kmh,
            max_distance_km=body.max_distance_km,
            preferred_terrain=_parse_terrain(body.preferred_terrain),
            preferred_direction=_parse_direction(body.preferred_direction),
            home_coordinates=home_coords,
        )
        try:
            profile = await manage_profile_uc.update(domain_req)
        except ProfileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(
                    "PROFILE_NOT_FOUND", f"Profile {profile_id} not found"
                ),
            ) from None
        return _build_profile_response(profile)

    @router.delete(
        "/profiles/{profile_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={404: {"model": ErrorResponse}},
    )
    async def delete_profile(profile_id: str):
        try:
            uid = UUID(profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=_error("VALIDATION_ERROR", f"Invalid UUID: {profile_id}"),
            ) from None
        try:
            await manage_profile_uc.delete(uid)
        except ProfileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(
                    "PROFILE_NOT_FOUND", f"Profile {profile_id} not found"
                ),
            ) from None

    # -----------------------------------------------------------------------
    #  Routes
    # -----------------------------------------------------------------------

    @router.post(
        "/routes/plan",
        response_model=RouteResponse,
        status_code=status.HTTP_201_CREATED,
        responses={404: {"model": ErrorResponse}},
    )
    async def plan_route(body: PlanRouteRequest):
        try:
            profile_id = UUID(body.profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=_error(
                    "VALIDATION_ERROR",
                    f"Invalid profile_id UUID: {body.profile_id}",
                ),
            ) from None

        start_coords = None
        if body.start_latitude is not None and body.start_longitude is not None:
            start_coords = Coordinates(
                latitude=body.start_latitude, longitude=body.start_longitude
            )

        domain_req = PlanRouteUCRequest(
            profile_id=profile_id,
            activity_type=_parse_activity_type(body.activity_type),
            max_distance_km=body.max_distance_km,
            max_duration_min=body.max_duration_min,
            preferred_direction=_parse_direction(body.preferred_direction),
            terrain_type=_parse_terrain(body.terrain_type),
            start_coordinates=start_coords,
        )
        try:
            route = await plan_route_uc.execute(domain_req)
        except ProfileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(
                    "PROFILE_NOT_FOUND",
                    f"Profile {body.profile_id} not found",
                ),
            ) from None
        return _build_route_response(route)

    @router.get(
        "/routes/{route_id}",
        response_model=RouteResponse,
        responses={404: {"model": ErrorResponse}},
    )
    async def get_route(route_id: str):
        try:
            uid = UUID(route_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=_error("VALIDATION_ERROR", f"Invalid UUID: {route_id}"),
            ) from None
        try:
            route = await plan_route_uc.get_route(uid)
        except RouteNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=_error(
                    "ROUTE_NOT_FOUND", f"Route {route_id} not found"
                ),
            ) from None
        return _build_route_response(route)

    return router
