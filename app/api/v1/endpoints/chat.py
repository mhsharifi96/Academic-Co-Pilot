import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage

from app.api.schemas.chat import ChatRequest, ChatResponse, ResumeRequest
from app.agents.hitl import extract_interrupt, build_resume_command_value
from app.core.sessions import session_manager

router = APIRouter()


def _get_agent(request: Request):
    """Return the shared agent built during the app lifespan."""
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent is not ready yet.")
    return agent


def _final_text(result: Dict[str, Any]) -> str:
    """Extract the last AI message text from a graph result."""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


async def _build_context_message(session_id: str) -> Optional[str]:
    """Build the per-turn system context listing the session's files."""
    files = await session_manager.get_files(session_id)
    if not files:
        return "Session files: (none uploaded yet — the user can upload PDFs/CSVs)."
    listed = "\n".join(f"  - {f}" for f in files)
    return f"Files available in this session:\n{listed}"


async def _to_response(result: Dict[str, Any], session_id: str) -> ChatResponse:
    """Turn a graph result into a ChatResponse, handling HITL interrupts."""
    interrupt = extract_interrupt(result)
    if interrupt:
        await session_manager.set_pending_interrupt(session_id, interrupt)
        return ChatResponse(
            response=interrupt["message"],
            session_id=session_id,
            status="interrupted",
            interrupt=interrupt,
            output=None,
        )

    # Completed normally — clear any stale interrupt marker.
    await session_manager.set_pending_interrupt(session_id, None)
    return ChatResponse(
        response=_final_text(result),
        session_id=session_id,
        status="complete",
        output=None,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """
    Main chat endpoint.  Conversation state is persisted automatically per
    ``session_id`` (LangGraph checkpointer), so you only send the new message —
    no need to replay history.

    If the agent decides to run a sensitive tool (analytics_sandbox,
    screen_abstracts_csv, ingest_pdf), the response comes back with
    ``status="interrupted"`` and an ``interrupt`` payload.  Approve or reject it
    via ``POST /chat/resume``.
    """
    agent = _get_agent(http_request)
    session_id = request.session_id or str(uuid.uuid4())
    await session_manager.get_or_create(session_id)

    try:
        context_message = await _build_context_message(session_id)
        result = await agent.run(
            request.message,
            session_id=session_id,
            context_message=context_message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

    return await _to_response(result, session_id)


@router.post("/chat/resume", response_model=ChatResponse)
async def resume(request: ResumeRequest, http_request: Request):
    """
    Resume a conversation that is paused awaiting human approval of a tool call.

    - ``approve``: run the tool as the agent requested.
    - ``edit``: run the tool with ``edited_args`` instead.
    - ``reject``: skip the tool; ``reason`` is passed back to the agent.
    """
    agent = _get_agent(http_request)
    pending = await session_manager.get_pending_interrupt(request.session_id)
    if not pending:
        raise HTTPException(
            status_code=409,
            detail="No tool call is awaiting approval for this session.",
        )

    if request.decision == "edit" and not request.edited_args:
        raise HTTPException(
            status_code=400,
            detail="decision='edit' requires 'edited_args'.",
        )

    resume_value = build_resume_command_value(
        decision=request.decision,
        edited_args=request.edited_args,
        reason=request.reason,
        pending_actions=pending.get("pending_actions"),
    )

    try:
        result = await agent.resume(request.session_id, resume_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Resume Error: {str(e)}")

    return await _to_response(result, request.session_id)
