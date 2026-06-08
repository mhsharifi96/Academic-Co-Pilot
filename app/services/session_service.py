"""
DB operations for per-user chat-session ownership metadata.

These wrap the ``ChatSession`` table (ownership + title + timestamps).  The
conversation messages themselves are owned by the LangGraph checkpointer, keyed
by ``thread_id == ChatSession.id``.
"""

from typing import List, Optional

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import ChatSession, User


async def get_owned_session(
    db: AsyncSession, user: User, session_id: str
) -> Optional[ChatSession]:
    """Return the session iff it exists AND belongs to ``user``; else None."""
    cs = await db.get(ChatSession, session_id)
    if cs is None or cs.user_id != user.id:
        return None
    return cs


async def list_user_sessions(db: AsyncSession, user: User) -> List[ChatSession]:
    """All of the user's sessions, newest-updated first."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def ensure_session(
    db: AsyncSession,
    user: User,
    session_id: str,
    title: Optional[str] = None,
) -> ChatSession:
    """
    Create the session row if missing (owned by ``user``), otherwise touch it.
    If a row with this id exists but belongs to someone else, raise PermissionError.
    """
    cs = await db.get(ChatSession, session_id)
    if cs is None:
        cs = ChatSession(
            id=session_id,
            user_id=user.id,
            title=(title or "New chat")[:120],
        )
        db.add(cs)
    elif cs.user_id != user.id:
        raise PermissionError("Session belongs to another user.")
    elif title and (not cs.title or cs.title == "New chat"):
        cs.title = title[:120]
    # Bump the activity timestamp so this session sorts to the top of the list.
    cs.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(cs)
    return cs


async def rename_session(
    db: AsyncSession, user: User, session_id: str, title: str
) -> Optional[ChatSession]:
    cs = await get_owned_session(db, user, session_id)
    if cs is None:
        return None
    cs.title = title[:120]
    await db.commit()
    await db.refresh(cs)
    return cs


async def delete_session_row(db: AsyncSession, user: User, session_id: str) -> bool:
    cs = await get_owned_session(db, user, session_id)
    if cs is None:
        return False
    await db.delete(cs)
    await db.commit()
    return True
