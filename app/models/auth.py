"""
ORM models for authentication and per-user session ownership.

Note: conversation *messages* are NOT stored here — they live in the LangGraph
checkpointer tables, keyed by ``thread_id == ChatSession.id``.  ``ChatSession``
only records ownership and list metadata (title, timestamps).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
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
    # Remaining usage credit in USD. Each chat turn deducts its measured token
    # cost (see app/services/billing_service.py); admins top it back up.
    balance: Mapped[float] = mapped_column(
        Float,
        default=lambda: settings.DEFAULT_USER_BALANCE,
        server_default=text("0.5"),
        nullable=False,
    )
    # Admins can view all users and adjust balances via /api/v1/admin/*.
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
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


class UsageRecord(Base):
    """
    One row per billed agent turn: the token usage measured for that turn and
    the dollar cost deducted from the user's balance. Kept for auditing and to
    power the admin view; the authoritative balance lives on ``User.balance``.
    """

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="usage_records")
