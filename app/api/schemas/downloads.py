"""Pydantic request/response models for the PDF download queue."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DownloadRequest(BaseModel):
    session_id: str
    doi: str


class DownloadJobOut(BaseModel):
    id: str
    session_id: str
    doi: str
    status: str
    service_tier: str
    request_number: int
    priority_round: Optional[int] = None
    attempt_count: int
    available_at: datetime
    target_deadline: datetime
    failure_code: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DownloadCreateResponse(BaseModel):
    job: DownloadJobOut
    quota_remaining: int
    # True when an identical active request already existed (no new job/quota).
    deduplicated: bool = False


class DownloadListResponse(BaseModel):
    jobs: List[DownloadJobOut]
    quota_remaining: int
