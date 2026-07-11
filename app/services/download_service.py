"""
Business logic for the provider PDF download queue.

Split into two layers:

* **Pure functions** (``normalize_doi``, ``schedule_for``, ``deterministic_jitter``,
  ``pick_next``, ``retry_plan``) contain the quota/scheduling/fairness rules and
  take plain values — no DB, no clock hidden inside — so they are unit-tested
  offline (``tests/test_downloads.py``).
* **DB wrappers** (``create_download_request``, ``select_next_job``, the
  ``mark_*`` helpers, and the read helpers) query Postgres via the async session
  and delegate the actual decisions to the pure functions.

The single background worker (``app/core/download_worker.py``) drives these.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth import User
from app.models.downloads import (
    ACTIVE_STATUSES,
    ELIGIBLE_STATUSES,
    FAILURE_PDF_NOT_FOUND,
    PROCESSED_STATUSES,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_RETRY_SCHEDULED,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    TIER_FAST,
    TIER_STANDARD,
    DownloadJob,
)

# Matches a bare DOI (same shape as app/tools/literature.py:_DOI_RE).
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


class QuotaExceeded(Exception):
    """The user has used up their download quota for the current window."""


class InvalidDOI(Exception):
    """The supplied string is not a recognisable DOI."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_float_list(raw: str) -> List[float]:
    out: List[float] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part:
            try:
                out.append(float(part))
            except ValueError:
                continue
    return out


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #
def normalize_doi(raw: str) -> str:
    """
    Normalise a user/agent supplied DOI to a bare ``10.xxxx/...`` form.

    Accepts ``doi:``-prefixed and ``https://doi.org/`` URL forms. Raises
    ``InvalidDOI`` if the result doesn't look like a DOI.
    """
    s = (raw or "").strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE)
    s = s.strip().rstrip(".,;:)]*")
    if not _DOI_RE.match(s):
        raise InvalidDOI(f"'{raw}' is not a valid DOI.")
    return s


def deterministic_jitter(
    user_id: str, request_number: int, max_minutes: int
) -> timedelta:
    """
    A stable, per-(user, request) jitter in ``[-max_minutes, +max_minutes]``.

    Uses a hash (NOT Python's salted ``hash()``) so the value is identical across
    processes and restarts, and differs between users so their scheduled jobs
    don't all become available at exactly the same moment.
    """
    if max_minutes <= 0:
        return timedelta(0)
    digest = hashlib.sha256(f"{user_id}:{request_number}".encode()).hexdigest()
    span = 2 * max_minutes + 1
    offset = int(digest, 16) % span - max_minutes
    return timedelta(minutes=offset)


@dataclass
class Schedule:
    service_tier: str
    priority_round: Optional[int]
    available_at: datetime
    target_deadline: datetime


def schedule_for(request_number: int, user_id: str, now: datetime) -> Schedule:
    """
    Decide tier / priority / timing for a user's Nth request in the window.

    * Requests 1..3  → FAST, priority_round = N, available now, deadline +1h.
    * Requests 4..N  → STANDARD, available_at spread across the next 24h at the
      configured hour offsets (plus deterministic per-user jitter), deadline +24h.
    """
    if request_number <= 3:
        return Schedule(
            service_tier=TIER_FAST,
            priority_round=request_number,
            available_at=now,
            target_deadline=now + timedelta(minutes=settings.FAST_TARGET_MINUTES),
        )

    offsets = _parse_float_list(settings.STANDARD_OFFSETS_HOURS) or [24.0]
    idx = min(request_number - 4, len(offsets) - 1)
    base = timedelta(hours=offsets[idx])
    jitter = deterministic_jitter(
        user_id, request_number, settings.SCHEDULE_JITTER_MINUTES
    )
    available_at = now + base + jitter
    # Never schedule before "now"; jitter could pull an early offset negative.
    if available_at < now:
        available_at = now
    return Schedule(
        service_tier=TIER_STANDARD,
        priority_round=None,
        available_at=available_at,
        target_deadline=now + timedelta(hours=settings.STANDARD_TARGET_HOURS),
    )


@dataclass
class RetryPlan:
    """Outcome of a failed attempt: either reschedule, or give up."""
    give_up: bool
    attempt_count: int
    available_at: Optional[datetime]  # set when give_up is False


def retry_plan(current_attempt_count: int, now: datetime) -> RetryPlan:
    """
    Given the attempt that just failed, decide whether to retry and when.

    Attempt N fails → if N < max, reschedule after ``DOWNLOAD_RETRY_DELAYS_MIN[N-1]``
    minutes (10, then 20); otherwise give up. The delay is expressed as a future
    ``available_at`` so the worker never sleeps — it moves on to other jobs.
    """
    new_count = current_attempt_count + 1
    if new_count >= settings.DOWNLOAD_MAX_ATTEMPTS:
        return RetryPlan(give_up=True, attempt_count=new_count, available_at=None)

    delays = _parse_float_list(settings.DOWNLOAD_RETRY_DELAYS_MIN) or [10.0, 20.0]
    delay_min = delays[min(new_count - 1, len(delays) - 1)]
    return RetryPlan(
        give_up=False,
        attempt_count=new_count,
        available_at=now + timedelta(minutes=delay_min),
    )


def pick_next(
    eligible: Sequence[DownloadJob],
    served_counts: Dict[str, int],
    fast_streak: int,
    now: datetime,
    *,
    fast_before_standard: Optional[int] = None,
    deadline_urgent_minutes: Optional[int] = None,
) -> Optional[DownloadJob]:
    """
    Pick the next job from an already-eligible set using the fairness rules.

    Selection order (an intentional approximation of the spec's "generally"):
      1. Deadline override — a FAST job within ``deadline_urgent_minutes`` of its
         target wins (earliest deadline first).
      2. Anti-starvation — after ``fast_before_standard`` FAST jobs, serve the
         oldest eligible STANDARD job.
      3. Otherwise prefer FAST, ordered by
         (priority_round, served_count[user], attempt_count, created_at).
         ``served_count`` rotates users within a round so no one monopolises the
         queue; ``attempt_count`` keeps retries behind others' first attempts.
      4. Fall back to the oldest eligible STANDARD job.

    ``eligible`` must already be filtered to ELIGIBLE_STATUSES with
    ``available_at <= now`` (the DB wrapper does this).
    """
    if not eligible:
        return None

    fbs = (
        fast_before_standard
        if fast_before_standard is not None
        else settings.FAST_BEFORE_STANDARD
    )
    urgent_min = (
        deadline_urgent_minutes
        if deadline_urgent_minutes is not None
        else settings.DEADLINE_URGENT_MINUTES
    )

    fast = [j for j in eligible if j.service_tier == TIER_FAST]
    standard = [j for j in eligible if j.service_tier == TIER_STANDARD]

    # 1. Urgent FAST jobs near their one-hour target jump the queue.
    urgent_cutoff = now + timedelta(minutes=urgent_min)
    urgent = [j for j in fast if j.target_deadline <= urgent_cutoff]
    if urgent:
        return min(urgent, key=lambda j: (j.target_deadline, j.created_at))

    # 2. Anti-starvation: don't let a stream of FAST jobs block STANDARD forever.
    if fast_streak >= fbs and standard:
        return min(standard, key=lambda j: (j.available_at, j.created_at))

    # 3. Prefer FAST with per-user fairness within each priority round.
    if fast:
        return min(
            fast,
            key=lambda j: (
                j.priority_round or 0,
                served_counts.get(j.user_id, 0),
                j.attempt_count,
                j.created_at,
            ),
        )

    # 4. Otherwise the oldest available STANDARD job.
    if standard:
        return min(standard, key=lambda j: (j.available_at, j.created_at))
    return None


# --------------------------------------------------------------------------- #
# DB wrappers
# --------------------------------------------------------------------------- #
def _window_start(now: datetime) -> datetime:
    return now - timedelta(hours=settings.DOWNLOAD_QUOTA_WINDOW_HOURS)


async def count_requests_in_window(
    db: AsyncSession, user_id: str, now: datetime
) -> int:
    """Number of originating requests this user made in the rolling window.

    Counts job rows (retries reuse a row, so they never inflate this) created
    since the window start — this is the quota tally.
    """
    result = await db.execute(
        select(func.count(DownloadJob.id)).where(
            DownloadJob.user_id == user_id,
            DownloadJob.created_at >= _window_start(now),
        )
    )
    return int(result.scalar_one())


async def find_active_job_for_doi(
    db: AsyncSession, user_id: str, doi: str
) -> Optional[DownloadJob]:
    """Return the user's in-flight (active) job for this DOI, if any."""
    result = await db.execute(
        select(DownloadJob)
        .where(
            DownloadJob.user_id == user_id,
            DownloadJob.doi == doi,
            DownloadJob.status.in_(ACTIVE_STATUSES),
        )
        .order_by(DownloadJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def quota_remaining(db: AsyncSession, user_id: str, now: datetime) -> int:
    used = await count_requests_in_window(db, user_id, now)
    return max(0, settings.DOWNLOAD_QUOTA_LIMIT - used)


@dataclass
class CreateResult:
    job: DownloadJob
    quota_remaining: int
    deduplicated: bool  # True when we returned an existing active job


async def create_download_request(
    db: AsyncSession, user: User, session_id: str, doi: str
) -> CreateResult:
    """
    Create (or dedupe) a download request for ``user`` in ``session_id``.

    * Bad DOI → ``InvalidDOI``.
    * Same DOI already active for this user → returns that job, no new quota spend.
    * Over quota → ``QuotaExceeded``.

    Otherwise inserts a job with tier/priority/schedule from ``schedule_for``.
    """
    doi_norm = normalize_doi(doi)  # raises InvalidDOI
    now = _now()

    existing = await find_active_job_for_doi(db, user.id, doi_norm)
    if existing is not None:
        return CreateResult(
            job=existing,
            quota_remaining=await quota_remaining(db, user.id, now),
            deduplicated=True,
        )

    used = await count_requests_in_window(db, user.id, now)
    if used >= settings.DOWNLOAD_QUOTA_LIMIT:
        raise QuotaExceeded(
            f"Download quota reached ({settings.DOWNLOAD_QUOTA_LIMIT} per "
            f"{settings.DOWNLOAD_QUOTA_WINDOW_HOURS}h). Try again later."
        )

    request_number = used + 1
    sched = schedule_for(request_number, user.id, now)
    job = DownloadJob(
        user_id=user.id,
        session_id=session_id,
        doi=doi_norm,
        status=STATUS_QUEUED,
        service_tier=sched.service_tier,
        request_number=request_number,
        priority_round=sched.priority_round,
        attempt_count=0,
        available_at=sched.available_at,
        target_deadline=sched.target_deadline,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return CreateResult(
        job=job,
        quota_remaining=max(0, settings.DOWNLOAD_QUOTA_LIMIT - request_number),
        deduplicated=False,
    )


async def _served_counts(db: AsyncSession) -> Dict[str, int]:
    """Per-user count of already-processed jobs (for fairness rotation)."""
    result = await db.execute(
        select(DownloadJob.user_id, func.count(DownloadJob.id))
        .where(DownloadJob.status.in_(PROCESSED_STATUSES))
        .group_by(DownloadJob.user_id)
    )
    return {row[0]: int(row[1]) for row in result.all()}


async def select_next_job(
    db: AsyncSession, fast_streak: int
) -> Optional[DownloadJob]:
    """Fetch the eligible set and choose the next job to run (or None)."""
    now = _now()
    result = await db.execute(
        select(DownloadJob).where(
            DownloadJob.status.in_(ELIGIBLE_STATUSES),
            DownloadJob.available_at <= now,
        )
    )
    eligible = list(result.scalars().all())
    if not eligible:
        return None
    served = await _served_counts(db)
    return pick_next(eligible, served, fast_streak, now)


async def mark_running(db: AsyncSession, job: DownloadJob) -> None:
    job.status = STATUS_RUNNING
    await db.commit()


async def schedule_retry(
    db: AsyncSession, job: DownloadJob, plan: RetryPlan
) -> None:
    job.attempt_count = plan.attempt_count
    job.status = STATUS_RETRY_SCHEDULED
    job.available_at = plan.available_at
    await db.commit()


async def mark_succeeded(
    db: AsyncSession, job: DownloadJob, file_path: str
) -> None:
    job.status = STATUS_SUCCEEDED
    job.file_path = file_path
    job.failure_code = None
    await db.commit()


async def mark_failed(
    db: AsyncSession, job: DownloadJob, failure_code: str, attempt_count: int
) -> None:
    job.status = STATUS_FAILED
    job.failure_code = failure_code
    job.attempt_count = attempt_count
    await db.commit()


async def get_job(
    db: AsyncSession, user: User, job_id: str
) -> Optional[DownloadJob]:
    """Return a job iff it exists AND belongs to ``user`` (else None)."""
    job = await db.get(DownloadJob, job_id)
    if job is None or job.user_id != user.id:
        return None
    return job


async def list_jobs_for_session(
    db: AsyncSession, user: User, session_id: str
) -> List[DownloadJob]:
    """All of the user's download jobs for a session, newest first."""
    result = await db.execute(
        select(DownloadJob)
        .where(
            DownloadJob.user_id == user.id,
            DownloadJob.session_id == session_id,
        )
        .order_by(DownloadJob.created_at.desc())
    )
    return list(result.scalars().all())


async def list_jobs_for_user(db: AsyncSession, user: User) -> List[DownloadJob]:
    """All download jobs owned by ``user`` across every session, newest first."""
    result = await db.execute(
        select(DownloadJob)
        .where(DownloadJob.user_id == user.id)
        .order_by(DownloadJob.created_at.desc())
    )
    return list(result.scalars().all())
