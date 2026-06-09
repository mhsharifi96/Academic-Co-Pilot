import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sessions import session_manager
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.services.session_service import (
    delete_session_row,
    get_owned_session,
    list_user_sessions,
    rename_session,
)

router = APIRouter()


class SessionFile(BaseModel):
    """A single file associated with a session."""
    path: str
    filename: str
    type: str  # "pdf" | "csv" | "other"


class SessionFilesResponse(BaseModel):
    session_id: str
    files: List[SessionFile]


class PlanItem(BaseModel):
    """One step in the agent's task plan."""
    text: str
    status: str  # "pending" | "in_progress" | "done"


class SessionPlanResponse(BaseModel):
    session_id: str
    plan: List[PlanItem]


class SessionSummary(BaseModel):
    """A session in the user's list."""
    id: str
    title: str
    updated_at: str


class RenameRequest(BaseModel):
    title: str


class HistoryMessage(BaseModel):
    """One turn of the conversation, shaped for the UI."""
    role: str  # "user" | "assistant"
    content: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[HistoryMessage]
    interrupted: bool = False
    interrupt: Optional[dict] = None


class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted: bool


def _file_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    return ext if ext in ("pdf", "csv") else "other"


def _msg_text(content) -> str:
    """Flatten LangChain message content (str or list of parts) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "".join(parts)
    return str(content) if content else ""


@router.get("/sessions", response_model=List[SessionSummary])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[SessionSummary]:
    """List the current user's chat sessions, newest-updated first."""
    rows = await list_user_sessions(db, current_user)
    return [
        SessionSummary(id=r.id, title=r.title, updated_at=r.updated_at.isoformat())
        for r in rows
    ]


@router.patch("/sessions/{session_id}", response_model=SessionSummary)
async def patch_session(
    session_id: str,
    body: RenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """Rename a session the user owns."""
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")
    cs = await rename_session(db, current_user, session_id, title)
    if cs is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return SessionSummary(id=cs.id, title=cs.title, updated_at=cs.updated_at.isoformat())


@router.get("/sessions/{session_id}/files", response_model=SessionFilesResponse)
async def list_files(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionFilesResponse:
    """
    List the files uploaded in a session the user owns.

    Used by the web UI to populate the file sidebar and the ``@``-mention
    autocomplete (so file references survive a page reload).
    """
    if await get_owned_session(db, current_user, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    paths = await session_manager.get_files(session_id)
    files = [
        SessionFile(
            path=p,
            filename=os.path.basename(p),
            type=_file_type(p),
        )
        for p in paths
    ]
    return SessionFilesResponse(session_id=session_id, files=files)


@router.get("/sessions/{session_id}/plan", response_model=SessionPlanResponse)
async def get_plan(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionPlanResponse:
    """
    Return the agent's current task plan for a session the user owns.

    The plan is the agent-authored checklist (written via ``write_plan`` and
    updated via ``update_plan``); the web UI renders it as a live progress
    sidebar.  Empty list when the agent hasn't created a plan yet.
    """
    if await get_owned_session(db, current_user, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    plan = await session_manager.get_plan(session_id)
    items = [
        PlanItem(text=item.get("text", ""), status=item.get("status", "pending"))
        for item in plan
    ]
    return SessionPlanResponse(session_id=session_id, plan=items)


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_history(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionHistoryResponse:
    """
    Return a session's conversation transcript so the UI can reload an old chat.

    History is owned by the LangGraph checkpointer (keyed by
    ``thread_id == session_id``); we read the latest state and project it to a
    simple ``user``/``assistant`` message list.  Note: long histories may have
    been compressed by ``SummarizationMiddleware``, so very old turns can appear
    as a summary rather than verbatim.
    """
    if await get_owned_session(db, current_user, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        return SessionHistoryResponse(session_id=session_id, messages=[])

    config = {"configurable": {"thread_id": session_id}}
    try:
        state = await agent.agent.aget_state(config)
    except Exception:
        return SessionHistoryResponse(session_id=session_id, messages=[])

    raw_messages = (state.values or {}).get("messages", []) if state else []
    messages: List[HistoryMessage] = []
    for m in raw_messages:
        if isinstance(m, HumanMessage):
            role = "user"
        elif isinstance(m, AIMessage):
            role = "assistant"
        else:
            continue  # skip System/Tool messages
        text = _msg_text(m.content)
        if text.strip():
            messages.append(HistoryMessage(role=role, content=text))

    # The thread is paused on an approval if the graph has pending work.
    interrupted = bool(getattr(state, "next", None)) if state else False
    pending = await session_manager.get_pending_interrupt(session_id)

    return SessionHistoryResponse(
        session_id=session_id,
        messages=messages,
        interrupted=interrupted and pending is not None,
        interrupt=pending if interrupted else None,
    )


@router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeleteSessionResponse:
    """
    Permanently delete a session the user owns: its conversation checkpoints, its
    uploaded files on disk (``data/<session_id>/``), the in-memory metadata, and
    the ownership row.
    """
    if await get_owned_session(db, current_user, session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # 1. Drop conversation checkpoints from the saver.
    saver = getattr(request.app.state, "checkpointer", None)
    if saver is not None and hasattr(saver, "adelete_thread"):
        try:
            await saver.adelete_thread(session_id)
        except Exception:
            pass  # best-effort: still clear files + metadata below

    # 2. Remove the session's upload directory.
    upload_dir = os.path.join("data", session_id)
    if os.path.isdir(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)

    # 3. Forget in-memory session metadata + the ownership row.
    await session_manager.remove(session_id)
    await delete_session_row(db, current_user, session_id)

    return DeleteSessionResponse(session_id=session_id, deleted=True)
