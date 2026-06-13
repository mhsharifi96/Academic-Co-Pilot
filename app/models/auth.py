"""
ORM models for authentication and per-user session ownership.

Note: conversation *messages* are NOT stored here — they live in the LangGraph
checkpointer tables, keyed by ``thread_id == ChatSession.id``.  ``ChatSession``
only records ownership and list metadata (title, timestamps).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    # id == the session_id / LangGraph thread_id (caller-supplied UUID string).
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String, default="New chat")
    # Which agent drives this session: "academic" (default) or "deep".
    # Bound at session creation (chosen in the UI before the first message) and
    # immutable thereafter — a thread is only ever run by the agent it was made
    # with, which keeps the two graphs' checkpoint state schemas from clashing.
    agent_type: Mapped[str] = mapped_column(
        String, default="academic", server_default="academic", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="sessions")
