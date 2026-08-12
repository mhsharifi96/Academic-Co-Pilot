"""Authentication endpoints: register, login, and current-user."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    get_user_by_email,
    hash_password,
    verify_password,
)
from app.models.auth import User
from app.services.site_settings_service import (
    get_site_settings,
    registration_allowed,
)

router = APIRouter()


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: str
    email: EmailStr
    balance: float
    is_admin: bool


def _user_out(user: User) -> "UserOut":
    return UserOut(
        id=user.id,
        email=user.email,
        balance=user.balance,
        is_admin=user.is_admin,
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AuthConfigOut(BaseModel):
    """Public flags the login screen needs before anyone is signed in."""

    registration_open: bool


@router.get("/auth/config", response_model=AuthConfigOut)
async def auth_config(db: AsyncSession = Depends(get_db)):
    """Unauthenticated: tells the UI whether to offer the sign-up form."""
    settings_row = await get_site_settings(db)
    user_count = await db.scalar(select(func.count()).select_from(User))
    return AuthConfigOut(
        registration_open=registration_allowed(
            settings_row.registration_open, user_count or 0
        )
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(creds: Credentials, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, creds.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    # The very first account to register becomes the admin so the deployment is
    # manageable out of the box (subsequent admins are granted from the admin UI).
    is_first_user = (
        await db.scalar(select(func.count()).select_from(User))
    ) == 0
    # Admins can close sign-up site-wide from /admin/settings; the first account
    # is always allowed through so a fresh deployment can bootstrap its admin.
    settings_row = await get_site_settings(db)
    if not registration_allowed(
        settings_row.registration_open, 0 if is_first_user else 1
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is currently closed. Please contact an administrator.",
        )
    user = User(
        email=creds.email,
        hashed_password=hash_password(creds.password),
        is_admin=is_first_user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=_user_out(user),
    )


@router.post("/auth/login", response_model=TokenResponse)
async def login(creds: Credentials, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, creds.email)
    if user is None or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        user=_user_out(user),
    )


@router.get("/auth/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)
