"""
Endpoints for the provider PDF download queue.

The provider token is a backend secret and is never referenced here — clients
only ever submit a DOI and a session id, and poll for job status. The actual
download + ingestion happens in the background worker.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.downloads import (
    DownloadCreateResponse,
    DownloadJobOut,
    DownloadListResponse,
    DownloadRequest,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.services import download_service as svc
from app.services.session_service import get_owned_session

router = APIRouter()


@router.post("/downloads", response_model=DownloadCreateResponse)
async def create_download(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a PDF download for a DOI, attaching the result to ``session_id``.

    Dedupes an already-active request for the same DOI (no extra quota), enforces
    the per-user quota (429), and rejects malformed DOIs (400).
    """
    owned = await get_owned_session(db, current_user, request.session_id)
    if owned is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        result = await svc.create_download_request(
            db, current_user, request.session_id, request.doi
        )
    except svc.InvalidDOI as e:
        raise HTTPException(status_code=400, detail=str(e))
    except svc.QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))

    return DownloadCreateResponse(
        job=DownloadJobOut.model_validate(result.job),
        quota_remaining=result.quota_remaining,
        deduplicated=result.deduplicated,
    )


@router.get("/downloads/{job_id}", response_model=DownloadJobOut)
async def get_download(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return one download job's current status (ownership-checked, for polling)."""
    job = await svc.get_job(db, current_user, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found.")
    return DownloadJobOut.model_validate(job)


@router.get("/downloads", response_model=DownloadListResponse)
async def list_downloads(
    session_id: str = Query(..., description="Conversation to list jobs for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all download jobs for a session (drives the in-chat status + failure UX)."""
    owned = await get_owned_session(db, current_user, session_id)
    if owned is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    jobs = await svc.list_jobs_for_session(db, current_user, session_id)
    remaining = await svc.quota_remaining(
        db, current_user.id, datetime.now(timezone.utc)
    )
    return DownloadListResponse(
        jobs=[DownloadJobOut.model_validate(j) for j in jobs],
        quota_remaining=remaining,
    )
