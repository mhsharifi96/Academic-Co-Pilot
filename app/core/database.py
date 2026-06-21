"""
Async SQLAlchemy engine, session factory and declarative base.

This is separate from the vector store (``app/core/db.py``, which uses a sync
psycopg2 connection via PGVector) and from the LangGraph checkpointer.  Here we
own the application's own tables: users and chat-session ownership metadata.

The engine uses the psycopg **v3** async driver (``postgresql+psycopg://``),
derived from the same ``DATABASE_URL`` used elsewhere.
"""

from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def _async_url(url: str) -> str:
    """Rewrite a plain ``postgresql://`` URL to the async psycopg v3 driver."""
    if url.startswith("postgresql+"):
        return url  # already has an explicit driver
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


engine = create_async_engine(_async_url(settings.DATABASE_URL), pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all application models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def bootstrap_admin() -> None:
    """Grant admin to ``settings.ADMIN_EMAIL`` if that user exists.

    Called once on startup, after ``init_models``. Idempotent and order-
    independent: the designated account still registers normally, and this just
    flips its ``is_admin`` flag so a production deployment always has a known
    admin regardless of who registered first. No-op when ``ADMIN_EMAIL`` is
    unset or the matching user hasn't registered yet.
    """
    if not settings.ADMIN_EMAIL:
        return

    from sqlalchemy import select

    from app.models.auth import User

    email = settings.ADMIN_EMAIL.strip()
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is not None and not user.is_admin:
            user.is_admin = True
            await session.commit()


async def init_models() -> None:
    """Create application tables if they don't exist (called on startup)."""
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # ``create_all`` never ALTERs an existing table, so add columns that were
        # introduced after a table first shipped. Postgres supports IF NOT EXISTS,
        # making this a safe no-op on fresh and already-migrated databases alike.
        await conn.execute(
            text(
                "ALTER TABLE chat_sessions "
                "ADD COLUMN IF NOT EXISTS agent_type VARCHAR "
                "NOT NULL DEFAULT 'academic'"
            )
        )
        # Per-user balance / admin flag, added after the users table first
        # shipped. Same IF NOT EXISTS pattern — safe on fresh and existing DBs.
        await conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS balance DOUBLE PRECISION "
                "NOT NULL DEFAULT 0.5"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS is_admin BOOLEAN "
                "NOT NULL DEFAULT FALSE"
            )
        )
