"""
ORM model for the provider PDF download queue.

A ``DownloadJob`` is one user's request to fetch a paper's full-text PDF from the
external provider by DOI. Jobs are processed by a single background worker
(``app/core/download_worker.py``) that runs them strictly one-at-a-time with
priority/fairness scheduling and a bounded delayed-retry policy. On success the
PDF is pushed through the existing ingestion pipeline and attached to the job's
conversation. Business logic lives in ``app/services/download_service.py``.

This is an *app table* (async SQLAlchemy, same ``Base`` as ``users`` /
``chat_sessions``) — distinct from the vector store and the LangGraph
checkpointer.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Lifecycle statuses. Active statuses are eligible for the worker to pick up;
# SUCCEEDED / FAILED are terminal.
STATUS_QUEUED = "QUEUED"
STATUS_RUNNING = "RUNNING"
STATUS_RETRY_SCHEDULED = "RETRY_SCHEDULED"
STATUS_SUCCEEDED = "SUCCEEDED"
STATUS_FAILED = "FAILED"

ACTIVE_STATUSES = (STATUS_QUEUED, STATUS_RUNNING, STATUS_RETRY_SCHEDULED)
ELIGIBLE_STATUSES = (STATUS_QUEUED, STATUS_RETRY_SCHEDULED)
PROCESSED_STATUSES = (STATUS_RUNNING, STATUS_SUCCEEDED, STATUS_FAILED)

TIER_FAST = "FAST"
TIER_STANDARD = "STANDARD"

# Terminal failure codes surfaced to the UI.
FAILURE_PDF_NOT_FOUND = "PDF_NOT_FOUND"
FAILURE_PROVIDER_ERROR = "PROVIDER_ERROR"


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Conversation to attach the fetched PDF to (== session_id == thread_id).
    session_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    # Normalized DOI (see download_service.normalize_doi).
    doi: Mapped[str] = mapped_column(String, index=True, nullable=False)

    status: Mapped[str] = mapped_column(
        String, default=STATUS_QUEUED, nullable=False
    )
    service_tier: Mapped[str] = mapped_column(String, nullable=False)
    # The user's Nth originating request within the current quota window (1..N).
    # Drives tier, priority and scheduling. Retries keep the original number.
    request_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # 1/2/3 for FAST jobs; NULL for STANDARD jobs.
    priority_round: Mapped[int] = mapped_column(Integer, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    target_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    failure_code: Mapped[str] = mapped_column(String, nullable=True)
    # Saved PDF path once the download + ingestion succeed.
    file_path: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        # Worker poll: "eligible jobs, soonest available first".
        Index("ix_download_jobs_status_available", "status", "available_at"),
        # Quota counting: "this user's requests in the rolling window".
        Index("ix_download_jobs_user_created", "user_id", "created_at"),
    )
