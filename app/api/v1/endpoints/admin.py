"""
Admin endpoints for managing users' balances and site-wide settings.

All routes require an admin (``get_current_admin`` → 403 otherwise). Kept small
and self-contained: list users, adjust a user's balance, toggle admin, and open
or close public registration.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.auth import User
from app.services.site_settings_service import (
    get_site_settings,
    set_registration_open,
)

router = APIRouter()


class AdminUserOut(BaseModel):
    id: str
    email: str
    balance: float
    is_admin: bool
    created_at: Optional[datetime] = None


class UpdateUserRequest(BaseModel):
    """Set the balance outright and/or change admin status. Both optional."""

    balance: Optional[float] = Field(default=None, ge=0)
    is_admin: Optional[bool] = None


class AdjustBalanceRequest(BaseModel):
    """Add (or subtract, if negative) credit to a user's balance."""

    amount: float


class SiteSettingsOut(BaseModel):
    registration_open: bool
    updated_at: Optional[datetime] = None


class UpdateSiteSettingsRequest(BaseModel):
    """Open or close public sign-up. Optional so the model can grow."""

    registration_open: Optional[bool] = None


def _to_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        balance=user.balance,
        is_admin=user.is_admin,
        created_at=user.created_at,
    )


@router.get("/admin/users", response_model=List[AdminUserOut])
async def list_users(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return [_to_out(u) for u in result.scalars().all()]


async def _get_user_or_404(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/admin/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(db, user_id)
    if body.balance is not None:
        user.balance = round(float(body.balance), 6)
    if body.is_admin is not None:
        # Guard against an admin accidentally demoting themselves and locking
        # everyone out — they can't remove their own admin flag here.
        if user.id == admin.id and not body.is_admin:
            raise HTTPException(
                status_code=400, detail="You cannot revoke your own admin access."
            )
        user.is_admin = body.is_admin
    await db.commit()
    await db.refresh(user)
    return _to_out(user)


@router.get("/admin/settings", response_model=SiteSettingsOut)
async def read_site_settings(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = await get_site_settings(db)
    return SiteSettingsOut(
        registration_open=row.registration_open, updated_at=row.updated_at
    )


@router.patch("/admin/settings", response_model=SiteSettingsOut)
async def update_site_settings(
    body: UpdateSiteSettingsRequest,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await set_registration_open(db, body.registration_open)
        if body.registration_open is not None
        else await get_site_settings(db)
    )
    return SiteSettingsOut(
        registration_open=row.registration_open, updated_at=row.updated_at
    )


@router.post("/admin/users/{user_id}/adjust-balance", response_model=AdminUserOut)
async def adjust_balance(
    user_id: str,
    body: AdjustBalanceRequest,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await _get_user_or_404(db, user_id)
    user.balance = round(max(0.0, user.balance + body.amount), 6)
    await db.commit()
    await db.refresh(user)
    return _to_out(user)
