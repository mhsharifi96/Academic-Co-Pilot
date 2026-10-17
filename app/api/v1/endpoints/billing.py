"""
Balance top-up requests paid in cryptocurrency.

User routes (``/billing/*``) create and follow a request; admin routes
(``/admin/topup-requests*``) send the payment email, confirm the payment (which
credits the balance) or reject it. The flow and statuses are documented in
``app/models/billing.py``; the rules live in ``app/services/topup_service.py``.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.models.auth import User
from app.models.billing import (
    OPEN_STATUSES,
    STATUS_AWAITING_PAYMENT,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PAID,
    STATUS_REJECTED,
    TopUpRequest,
)
from app.services import topup_service as svc

router = APIRouter()


class NetworkOut(BaseModel):
    key: str
    label: str


class TopUpOptionsOut(BaseModel):
    amounts: List[int]
    networks: List[NetworkOut]


class CreateTopUpRequest(BaseModel):
    email: EmailStr
    amount: float
    network: str


class MarkPaidRequest(BaseModel):
    tx_hash: Optional[str] = Field(default=None, max_length=200)


class SendPaymentEmailRequest(BaseModel):
    wallet_address: str = Field(min_length=10, max_length=200)
    note: Optional[str] = Field(default=None, max_length=2000)


class RejectRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=2000)


class TopUpOut(BaseModel):
    id: str
    user_id: str
    user_email: Optional[str] = None
    email: str
    amount: float
    network: str
    network_label: str
    status: str
    wallet_address: Optional[str] = None
    admin_note: Optional[str] = None
    tx_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SendPaymentEmailOut(BaseModel):
    request: TopUpOut
    email_sent: bool
    email_error: Optional[str] = None
    # Same message as a mailto: URL, so the admin can send it by hand.
    mailto: str


class ConfirmOut(BaseModel):
    request: TopUpOut
    user_balance: float


def _to_out(req: TopUpRequest, user_email: Optional[str] = None) -> TopUpOut:
    return TopUpOut(
        id=req.id,
        user_id=req.user_id,
        user_email=user_email,
        email=req.email,
        amount=req.amount,
        network=req.network,
        network_label=svc.CRYPTO_NETWORKS.get(req.network, req.network),
        status=req.status,
        wallet_address=req.wallet_address,
        admin_note=req.admin_note,
        tx_hash=req.tx_hash,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


def _require_transition(req: TopUpRequest, target: str) -> None:
    if not svc.can_transition(req.status, target):
        raise HTTPException(
            status_code=409,
            detail=f"This request is '{req.status}' and can't be moved to '{target}'.",
        )


# ---------------------------------------------------------------- user routes


@router.get("/billing/topup-options", response_model=TopUpOptionsOut)
async def topup_options(_: User = Depends(get_current_user)):
    return TopUpOptionsOut(
        amounts=list(svc.TOPUP_AMOUNTS),
        networks=[NetworkOut(key=k, label=v) for k, v in svc.CRYPTO_NETWORKS.items()],
    )


@router.get("/billing/topup-requests", response_model=List[TopUpOut])
async def list_my_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TopUpRequest)
        .where(TopUpRequest.user_id == current_user.id)
        .order_by(TopUpRequest.created_at.desc())
    )
    return [_to_out(r) for r in result.scalars().all()]


@router.post("/billing/topup-requests", response_model=TopUpOut, status_code=201)
async def create_request(
    body: CreateTopUpRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not svc.is_valid_amount(body.amount):
        raise HTTPException(
            status_code=400,
            detail=f"Amount must be one of {', '.join(f'${a}' for a in svc.TOPUP_AMOUNTS)}.",
        )
    if not svc.is_valid_network(body.network):
        raise HTTPException(status_code=400, detail="Unknown payment network.")
    # One open request at a time keeps the admin queue unambiguous.
    open_req = await db.scalar(
        select(TopUpRequest).where(
            TopUpRequest.user_id == current_user.id,
            TopUpRequest.status.in_(OPEN_STATUSES),
        )
    )
    if open_req is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have an open top-up request. Finish or cancel it first.",
        )
    req = TopUpRequest(
        user_id=current_user.id,
        email=str(body.email),
        amount=float(body.amount),
        network=body.network,
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return _to_out(req)


async def _get_own_request(
    db: AsyncSession, request_id: str, user: User
) -> TopUpRequest:
    req = await db.get(TopUpRequest, request_id)
    # Someone else's request is reported as missing, like sessions.
    if req is None or req.user_id != user.id:
        raise HTTPException(status_code=404, detail="Top-up request not found.")
    return req


@router.post("/billing/topup-requests/{request_id}/paid", response_model=TopUpOut)
async def mark_paid(
    request_id: str,
    body: MarkPaidRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_own_request(db, request_id, current_user)
    _require_transition(req, STATUS_PAID)
    req.status = STATUS_PAID
    req.tx_hash = (body.tx_hash or "").strip() or None
    await db.commit()
    await db.refresh(req)
    return _to_out(req)


@router.post("/billing/topup-requests/{request_id}/cancel", response_model=TopUpOut)
async def cancel_request(
    request_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_own_request(db, request_id, current_user)
    _require_transition(req, STATUS_CANCELLED)
    req.status = STATUS_CANCELLED
    await db.commit()
    await db.refresh(req)
    return _to_out(req)


# --------------------------------------------------------------- admin routes


@router.get("/admin/topup-requests", response_model=List[TopUpOut])
async def admin_list_requests(
    status: Optional[str] = Query(default=None),
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(TopUpRequest, User.email)
        .join(User, User.id == TopUpRequest.user_id)
        .order_by(TopUpRequest.created_at.desc())
    )
    if status == "open":
        stmt = stmt.where(TopUpRequest.status.in_(OPEN_STATUSES))
    elif status:
        stmt = stmt.where(TopUpRequest.status == status)
    result = await db.execute(stmt)
    return [_to_out(req, email) for req, email in result.all()]


async def _get_request_or_404(db: AsyncSession, request_id: str) -> TopUpRequest:
    # Row lock so two admins can't confirm (and credit) the same request twice.
    req = await db.scalar(
        select(TopUpRequest).where(TopUpRequest.id == request_id).with_for_update()
    )
    if req is None:
        raise HTTPException(status_code=404, detail="Top-up request not found.")
    return req


@router.post(
    "/admin/topup-requests/{request_id}/send-payment-email",
    response_model=SendPaymentEmailOut,
)
async def admin_send_payment_email(
    request_id: str,
    body: SendPaymentEmailRequest,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request_or_404(db, request_id)
    _require_transition(req, STATUS_AWAITING_PAYMENT)
    req.status = STATUS_AWAITING_PAYMENT
    req.wallet_address = body.wallet_address.strip()
    req.admin_note = (body.note or "").strip() or None
    await db.commit()
    await db.refresh(req)
    error = await svc.send_payment_email(req)
    return SendPaymentEmailOut(
        request=_to_out(req),
        email_sent=error is None,
        email_error=error,
        mailto=svc.mailto_link(req),
    )


@router.post("/admin/topup-requests/{request_id}/confirm", response_model=ConfirmOut)
async def admin_confirm(
    request_id: str,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request_or_404(db, request_id)
    _require_transition(req, STATUS_COMPLETED)
    user = await db.get(User, req.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user.balance = round(user.balance + req.amount, 6)
    req.status = STATUS_COMPLETED
    await db.commit()
    await db.refresh(req)
    await db.refresh(user)
    return ConfirmOut(request=_to_out(req, user.email), user_balance=user.balance)


@router.post("/admin/topup-requests/{request_id}/reject", response_model=TopUpOut)
async def admin_reject(
    request_id: str,
    body: RejectRequest,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    req = await _get_request_or_404(db, request_id)
    _require_transition(req, STATUS_REJECTED)
    req.status = STATUS_REJECTED
    if body.reason and body.reason.strip():
        req.admin_note = body.reason.strip()
    await db.commit()
    await db.refresh(req)
    return _to_out(req)
