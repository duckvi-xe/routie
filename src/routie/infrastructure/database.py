"""Async SQLAlchemy database engine, session factory, and declarative base.

Usage:
    engine = create_engine("sqlite+aiosqlite:///routie.db")
    factory = session_factory(engine)

    async with factory() as session:
        result = await session.execute(select(...))
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
#  Default database URL
# ---------------------------------------------------------------------------

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///routie.db"

# ---------------------------------------------------------------------------
#  Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    @classmethod
    def metadata_from_any(cls) -> Any:
        """Helper to get the metadata for the class hierarchy."""
        return cls.metadata


# ---------------------------------------------------------------------------
#  Factory helpers
# ---------------------------------------------------------------------------


def create_engine(database_url: str = DEFAULT_DATABASE_URL) -> AsyncEngine:
    """Create an async SQLAlchemy engine for the given database URL.

    For SQLite (the dev default) we disable connection pooling via NullPool
    to avoid ``QueuePool`` issues with concurrent async tasks.
    """
    if database_url.startswith("sqlite"):
        return create_async_engine(database_url, poolclass=NullPool, echo=False)
    return create_async_engine(database_url, echo=False)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to *engine*."""
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
#  Migration helpers (create / drop all tables)
# ---------------------------------------------------------------------------


async def create_all_tables(engine: AsyncEngine) -> None:
    """Create all tables defined in the Base metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables(engine: AsyncEngine) -> None:
    """Drop all tables defined in the Base metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
#  FastAPI dependency — async generator yielding a session
# ---------------------------------------------------------------------------


async def get_session(
    session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession]:
    """Yield a session from *session_maker* for FastAPI dependency injection."""
    async with session_maker() as session:
        yield session
