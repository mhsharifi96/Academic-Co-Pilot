"""
ORM models for admin-authored guided workflows ("wizards").

A ``Wizard`` is an ordered sequence of ``WizardStep`` rows. A user "runs" one:
``WizardRun`` tracks which step is current and how many user turns have been
spent on it, and ``WizardMessage`` persists the transcript as real rows — unlike
plain chat, whose history lives only in the LangGraph checkpointer and can be
compressed away by the summarization middleware.

Each run is backed by a ``ChatSession`` row (``agent_type="wizard"``) whose id is
``WizardRun.session_id``; that id is the LangGraph ``thread_id`` and the
``data/<session_id>/`` upload directory key, so file uploads and the existing
history/plan endpoints work on a wizard thread unchanged. Business logic lives
in ``app/services/wizard_service.py``.

These are *app tables* (async SQLAlchemy, same ``Base`` as ``users`` /
``chat_sessions``) — distinct from the vector store and the checkpointer.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Run lifecycle. ACTIVE is the only status that accepts new turns; COMPLETED is
# reached by exhausting the last step's message cap; ABANDONED is a soft delete
# that keeps the transcript and the billing audit trail.
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_ABANDONED = "abandoned"

RESUMABLE_STATUSES = (STATUS_ACTIVE,)
RUN_STATUSES = (STATUS_ACTIVE, STATUS_COMPLETED, STATUS_ABANDONED)

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

# Supported content languages for the public landing page.
LANGUAGES = ("en", "fa")
DEFAULT_LANGUAGE = "en"

# ChatSession.agent_type marking a session that belongs to a wizard run. Such
# sessions are hidden from the chat sidebar and rejected by POST /chat — turns
# must go through the wizard endpoints so the step counter stays honest.
WIZARD_AGENT_TYPE = "wizard"


class Wizard(Base):
    """An admin-authored guided workflow, listed on the public landing page."""

    __tablename__ = "wizards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    # Internal admin label; never rendered to end users (they see title_*).
    name: Mapped[str] = mapped_column(String, nullable=False)

    title_en: Mapped[str] = mapped_column(
        String, default="", server_default="", nullable=False
    )
    title_fa: Mapped[str] = mapped_column(
        String, default="", server_default="", nullable=False
    )
    short_description_en: Mapped[str] = mapped_column(
        Text, default="", server_default="", nullable=False
    )
    short_description_fa: Mapped[str] = mapped_column(
        Text, default="", server_default="", nullable=False
    )

    # Landing-page presentation: an icon key the UI maps to an inline SVG, and
    # the display order among published wizards.
    icon: Mapped[str] = mapped_column(String, nullable=True)
    position: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    # When False, only the deterministic jailbreak rules screen this wizard's
    # turns — the academic *scope* classifier is skipped, so an admin can author
    # a workflow the general guardrail would otherwise refuse as off-topic.
    enforce_scope_guardrail: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    steps: Mapped[list["WizardStep"]] = relationship(
        back_populates="wizard",
        cascade="all, delete-orphan",
        order_by="WizardStep.position",
    )

    __table_args__ = (
        # Landing page: "published wizards, in display order".
        Index("ix_wizards_published_position", "is_published", "position"),
    )


class WizardStep(Base):
    """One stage of a wizard: a prompt that steers the agent plus a turn cap."""

    __tablename__ = "wizard_steps"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    wizard_id: Mapped[str] = mapped_column(
        ForeignKey("wizards.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name_en: Mapped[str] = mapped_column(
        String, default="", server_default="", nullable=False
    )
    name_fa: Mapped[str] = mapped_column(
        String, default="", server_default="", nullable=False
    )
    # Injected as a per-turn SystemMessage while this step is current.
    guideline_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Max user turns allowed on this step; reaching it advances the run. NULL
    # (or <= 0) means unlimited — see wizard_service.apply_turn.
    max_messages: Mapped[int] = mapped_column(Integer, nullable=True)
    # 0-based execution order within the wizard. Deliberately NOT unique:
    # reordering rewrites the whole set, and a unique constraint would force a
    # temp-value shuffle to avoid transient collisions.
    position: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    wizard: Mapped["Wizard"] = relationship(back_populates="steps")

    __table_args__ = (Index("ix_wizard_steps_wizard_position", "wizard_id", "position"),)


class WizardRun(Base):
    """One user's traversal of one wizard."""

    __tablename__ = "wizard_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    wizard_id: Mapped[str] = mapped_column(
        ForeignKey("wizards.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # == ChatSession.id == LangGraph thread_id == data/<session_id>/ upload dir.
    # Kept distinct from ``id`` so the conversation thread is replaceable without
    # invalidating the run's identity.
    session_id: Mapped[str] = mapped_column(
        String, unique=True, index=True, default=_uuid, nullable=False
    )
    # NULL only if the step was deleted underneath a finished run (SET NULL).
    current_step_id: Mapped[str] = mapped_column(
        ForeignKey("wizard_steps.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String, default=STATUS_ACTIVE, server_default=STATUS_ACTIVE, nullable=False
    )
    # User turns spent on ``current_step_id``; reset to 0 on each advance.
    step_message_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    messages: Mapped[list["WizardMessage"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WizardMessage.created_at",
    )

    __table_args__ = (
        # "my runs, newest first" and the admin's active-run guards.
        Index("ix_wizard_runs_user_status", "user_id", "status"),
        # The start-or-resume lookup.
        Index("ix_wizard_runs_user_wizard_status", "user_id", "wizard_id", "status"),
    )


class WizardMessage(Base):
    """One persisted turn of a run's transcript."""

    __tablename__ = "wizard_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("wizard_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # The step that was CURRENT when this turn happened — both the user message
    # and its reply carry it, even when the turn triggers an advance.
    step_id: Mapped[str] = mapped_column(
        ForeignKey("wizard_steps.id", ondelete="SET NULL"), index=True, nullable=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # ROLE_USER | ROLE_ASSISTANT
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    run: Mapped["WizardRun"] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_wizard_messages_run_created", "run_id", "created_at"),)
