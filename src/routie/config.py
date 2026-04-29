"""Routie configuration.

Settings are loaded from environment variables with sensible defaults
for local development.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from os import environ


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    host: str = field(default_factory=lambda: environ.get("HOST", "0.0.0.0"))
    port: int = field(
        default_factory=lambda: int(environ.get("PORT", "8000"))
    )
    log_level: str = field(
        default_factory=lambda: environ.get("LOG_LEVEL", "info")
    )
    cors_origins: list[str] = field(
        default_factory=lambda: environ.get("CORS_ORIGINS", "*").split(",")
    )

    # Database
    database_url: str = field(
        default_factory=lambda: environ.get(
            "DATABASE_URL",
            "sqlite+aiosqlite:///routie.db",
        )
    )

    # Route provider selection
    route_provider: str = field(
        default_factory=lambda: environ.get("ROUTE_PROVIDER", "mock")
    )

    # Valhalla routing engine
    valhalla_url: str = field(
        default_factory=lambda: environ.get(
            "VALHALLA_URL", "http://valhalla:8002"
        )
    )

    # If True, create/run the SQL database; if False, use in-memory repos
    use_database: bool = field(
        default_factory=lambda: environ.get("USE_DB", "false").lower()
        in ("1", "true", "yes")
    )
