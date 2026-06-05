import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Request
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from app.core.sessions import session_manager

router = APIRouter()


class SessionFile(BaseModel):
    """A single file associated with a session."""
    path: str
    filename: str
    type: str  # "pdf" | "csv" | "other"


class SessionFilesResponse(BaseModel):
    session_id: str
    files: List[SessionFile]


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


@router.get("/sessions/{session_id}/files", response_model=SessionFilesResponse)
async def list_files(session_id: str) -> SessionFilesResponse:
    """
    List the files uploaded in a session.

    Used by the web UI to populate the file sidebar and the ``@``-mention
    autocomplete (so file references survive a page reload).  Returns an empty
    list for unknown sessions rather than 404 — a fresh session simply has no
    files yet.
    """
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


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_history(session_id: str, request: Request) -> SessionHistoryResponse:
    """
    Return a session's conversation transcript so the UI can reload an old chat.

    History is owned by the LangGraph checkpointer (keyed by
    ``thread_id == session_id``); we read the latest state and project it to a
    simple ``user``/``assistant`` message list.  Note: long histories may have
    been compressed by ``SummarizationMiddleware``, so very old turns can appear
    as a summary rather than verbatim.  Unknown sessions return an empty list.
    """
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
async def delete_session(session_id: str, request: Request) -> DeleteSessionResponse:
    """
    Permanently delete a session: its conversation checkpoints, its uploaded
    files on disk (``data/<session_id>/``), and its in-memory metadata.
    """
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

    # 3. Forget in-memory session metadata.
    await session_manager.remove(session_id)

    return DeleteSessionResponse(session_id=session_id, deleted=True)
