"""SQLAlchemy ORM models for Routie.

These models map to database tables and are used by the SQL repository
implementations. They are separate from the domain entities — conversion
happens in the repositories.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from routie.infrastructure.database import Base


class UserProfileModel(Base):
    """ORM model for the ``user_profiles`` table."""

    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(20), nullable=False)
    avg_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    max_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_terrain: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    preferred_direction: Mapped[str] = mapped_column(
        String(5), nullable=False, default="ANY"
    )
    home_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<UserProfileModel {self.name} [{self.activity_type}]>"


class RouteModel(Base):
    """ORM model for the ``routes`` table.

    Waypoints are stored as a JSON column — a list of ``[lat, lon]`` pairs.
    This is fine for SQLite; in PostgreSQL we'd likely use a separate table.
    """

    __tablename__ = "routes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_gain_m: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration_min: Mapped[int] = mapped_column(
        Float, nullable=False  # stored as Float to avoid SQLite int limitation
    )
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    waypoints_json: Mapped[list[list[float]] | None] = mapped_column(
        JSON, nullable=True
    )
    polyline: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RouteModel {self.name} ({self.distance_km:.1f} km)>"
