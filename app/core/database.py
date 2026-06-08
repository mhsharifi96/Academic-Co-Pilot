"""
Async SQLAlchemy engine, session factory and declarative base.

This is separate from the vector store (``app/core/db.py``, which uses a sync
psycopg2 connection via PGVector) and from the LangGraph checkpointer.  Here we
own the application's own tables: users and chat-session ownership metadata.

The engine uses the psycopg **v3** async driver (``postgresql+psycopg://``),
derived from the same ``DATABASE_URL`` used elsewhere.
"""

from typing import AsyncGenerator
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


async def init_models() -> None:
    """Create application tables if they don't exist (called on startup)."""
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
