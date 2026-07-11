"""
Single background worker for the provider PDF download queue.

Exactly one worker, one job at a time (``worker count = 1``, concurrency ``1``):
the loop repeatedly asks ``download_service.select_next_job`` for the highest-
priority eligible job, calls the provider, and on success runs the PDF through the
existing ingestion pipeline and attaches it to the job's conversation.

Delayed retries never block the worker: a 404 reschedules the job with a future
``available_at`` (via ``retry_plan``) and the loop immediately moves on to other
eligible jobs — it never sleeps for the 10/20-minute delay.

The worker is started/stopped from ``app/main.py``'s lifespan and is guarded by
``settings.ENABLE_DOWNLOAD_WORKER`` (off in the offline test suite).
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.sessions import UPLOAD_ROOT, session_manager
from app.models.downloads import (
    FAILURE_PDF_NOT_FOUND,
    FAILURE_PROVIDER_ERROR,
    TIER_FAST,
    DownloadJob,
)
from app.services import download_service as svc
from app.tools.ingestor import ingest_pdf

logger = logging.getLogger("paperagent.download_worker")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_doi_filename(doi: str) -> str:
    """Turn a DOI into a filesystem-safe ``.pdf`` name."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", doi).strip("_") or "paper"
    return f"{stem}.pdf"


def _looks_like_pdf(content: bytes, content_type: str) -> bool:
    if content[:5] == b"%PDF-":
        return True
    return "application/pdf" in (content_type or "").lower() and bool(content)


class DownloadWorker:
    """Owns the asyncio task and the FAST/STANDARD anti-starvation streak."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._fast_streak = 0

    def start(self) -> None:
        if self._task is None:
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="download-worker")
            logger.info("Download worker started.")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            self._task = None
            logger.info("Download worker stopped.")

    # ------------------------------------------------------------------ #
    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                worked = await self._tick()
            except Exception:  # never let one bad iteration kill the loop
                logger.exception("Download worker iteration failed.")
                worked = False
            if not worked:
                # Nothing eligible right now — wait, but wake early on stop.
                try:
                    await asyncio.wait_for(
                        self._stop.wait(), timeout=settings.WORKER_POLL_SECONDS
                    )
                except asyncio.TimeoutError:
                    pass

    async def _tick(self) -> bool:
        """Process at most one job. Returns True if a job was processed."""
        async with AsyncSessionLocal() as db:
            job = await svc.select_next_job(db, self._fast_streak)
            if job is None:
                return False
            await self._process(db, job)
            # Anti-starvation bookkeeping: count FAST serves, reset on STANDARD.
            if job.service_tier == TIER_FAST:
                self._fast_streak += 1
            else:
                self._fast_streak = 0
            return True

    async def _process(self, db, job: DownloadJob) -> None:
        await svc.mark_running(db, job)
        doi = job.doi
        logger.info(
            "Downloading DOI %s (job %s, attempt %s)",
            doi, job.id, job.attempt_count + 1,
        )

        try:
            status_code, content, content_type = await self._fetch(doi)
        except Exception as e:
            logger.warning("Provider request failed for %s: %s", doi, e)
            await self._handle_failure(db, job, FAILURE_PROVIDER_ERROR)
            return

        if status_code == 200 and _looks_like_pdf(content, content_type):
            await self._handle_success(db, job, content)
        elif status_code == 404:
            await self._handle_failure(db, job, FAILURE_PDF_NOT_FOUND)
        else:
            logger.warning(
                "Provider returned %s for %s (not a usable PDF)", status_code, doi
            )
            await self._handle_failure(db, job, FAILURE_PROVIDER_ERROR)

    async def _fetch(self, doi: str) -> tuple[int, bytes, str]:
        """GET the PDF from the provider. Token stays server-side, here only."""
        url = f"{settings.PROVIDER_BASE_URL.rstrip('/')}/article/doi"
        params = {"token": settings.PROVIDER_TOKEN or "", "doi": doi}
        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            return resp.status_code, resp.content, resp.headers.get("content-type", "")

    async def _handle_success(self, db, job: DownloadJob, content: bytes) -> None:
        session_id = job.session_id
        upload_dir = os.path.join(UPLOAD_ROOT, session_id)
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, _safe_doi_filename(job.doi))
        with open(file_path, "wb") as fh:
            fh.write(content)

        # Ingest into the vector store (sync psycopg2 PGVector) off the event loop,
        # then register the file so it feeds the agent's per-turn context — the
        # same "attach to conversation" the /upload endpoint performs.
        msg = await asyncio.to_thread(ingest_pdf.invoke, {"file_path": file_path})
        if isinstance(msg, str) and msg.startswith("Error"):
            logger.warning("Ingestion failed for %s: %s", file_path, msg)
            await self._handle_failure(db, job, FAILURE_PROVIDER_ERROR)
            return

        await session_manager.add_files(session_id, [file_path])
        await svc.mark_succeeded(db, job, file_path)
        logger.info("Job %s succeeded: %s", job.id, file_path)

    async def _handle_failure(
        self, db, job: DownloadJob, failure_code: str
    ) -> None:
        plan = svc.retry_plan(job.attempt_count, _now())
        if plan.give_up:
            await svc.mark_failed(db, job, failure_code, plan.attempt_count)
            logger.info(
                "Job %s failed permanently (%s) after %s attempts",
                job.id, failure_code, plan.attempt_count,
            )
        else:
            await svc.schedule_retry(db, job, plan)
            logger.info(
                "Job %s rescheduled (attempt %s) for %s",
                job.id, plan.attempt_count, plan.available_at,
            )


# Module-level singleton, started/stopped by the app lifespan.
download_worker = DownloadWorker()
