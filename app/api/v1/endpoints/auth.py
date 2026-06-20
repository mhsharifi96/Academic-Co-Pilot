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
