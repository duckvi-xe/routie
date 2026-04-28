"""Routie configuration."""

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
