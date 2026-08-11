import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.chat import ChatRequest, ChatResponse, ResumeRequest
from app.agents.context import build_session_context, final_text
from app.agents.hitl import extract_interrupt, build_resume_command_value
from app.agents.guardrails import screen_message, REFUSAL_MESSAGE
from app.core.config import settings
from app.core.sessions import session_manager
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.models.wizard import WIZARD_AGENT_TYPE
from app.services.billing_service import charge_usage, has_sufficient_balance
from app.services.session_service import ensure_session, get_owned_session

router = APIRouter()


def _get_agent(request: Request, agent_type: str = "academic"):
    """Return the shared agent for ``agent_type`` ("academic" | "deep")."""
    attr = "deep_agent" if agent_type == "deep" else "agent"
    agent = getattr(request.app.state, attr, None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent is not ready yet.")
    return agent


def _reject_wizard_session(agent_type: str) -> None:
    """
    Wizard threads may only be advanced through the wizard endpoints.

    Otherwise a client could post here with a run's ``session_id`` and take
    unlimited free-form turns on the same thread while the step counter never
    moves and nothing lands in ``wizard_messages``.
    """
    if agent_type == WIZARD_AGENT_TYPE:
        raise HTTPException(
            status_code=409,
            detail=(
                "This conversation belongs to a wizard run; post to "
                "/api/v1/wizard-runs/{run_id}/messages instead."
            ),
        )


async def _to_response(
    result: Dict[str, Any], session_id: str, balance: Optional[float] = None
) -> ChatResponse:
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
            balance=balance,
        )

    # Completed normally — clear any stale interrupt marker.
    await session_manager.set_pending_interrupt(session_id, None)
    return ChatResponse(
        response=final_text(result),
        session_id=session_id,
        status="complete",
        output=None,
        balance=balance,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint.  Conversation state is persisted automatically per
    ``session_id`` (LangGraph checkpointer), so you only send the new message —
    no need to replay history.

    Requires authentication; the session is created under / verified against the
    current user.  If the agent decides to run a sensitive tool, the response
    comes back with ``status="interrupted"`` — approve or reject via
    ``POST /chat/resume``.
    """
    session_id = request.session_id or str(uuid.uuid4())

    # Create or verify ownership of this session, and title it from the first
    # message.  PermissionError → the session belongs to someone else.  The
    # agent_type is recorded on creation and bound to the session thereafter.
    try:
        cs = await ensure_session(
            db,
            current_user,
            session_id,
            title=request.message.strip()[:120],
            agent_type=request.agent_type,
        )
    except PermissionError:
        raise HTTPException(status_code=404, detail="Session not found.")

    _reject_wizard_session(cs.agent_type)

    # Always honour the session's bound agent, ignoring any mismatching request.
    agent = _get_agent(http_request, cs.agent_type)

    # Guardrail: refuse off-topic / jailbreak / abuse attempts before the agent
    # runs (and before any balance is spent).
    verdict = await screen_message(request.message)
    if not verdict.allowed:
        return ChatResponse(
            response=REFUSAL_MESSAGE,
            session_id=session_id,
            status="blocked",
            balance=current_user.balance if settings.ENABLE_BILLING else None,
        )

    # Balance gate: block when the user is already out of credit.
    if not has_sufficient_balance(current_user):
        raise HTTPException(
            status_code=402,
            detail=(
                "Your balance is exhausted. Please contact an administrator to "
                "top up your account before continuing."
            ),
        )

    await session_manager.get_or_create(session_id)

    try:
        context_message = await build_session_context(session_id)
        result, usage = await agent.run(
            request.message,
            session_id=session_id,
            context_message=context_message,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

    balance = await charge_usage(db, current_user, usage, session_id)
    return await _to_response(
        result, session_id, balance if settings.ENABLE_BILLING else None
    )


@router.post("/chat/resume", response_model=ChatResponse)
async def resume(
    request: ResumeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resume a conversation that is paused awaiting human approval of a tool call.

    - ``approve``: run the tool as the agent requested.
    - ``edit``: run the tool with ``edited_args`` instead.
    - ``reject``: skip the tool; ``reason`` is passed back to the agent.
    """
    # Must own the session being resumed.
    owned = await get_owned_session(db, current_user, request.session_id)
    if owned is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    _reject_wizard_session(owned.agent_type)
    # Resume on the session's bound agent (deep sessions never interrupt, but
    # this keeps the selection correct regardless).
    agent = _get_agent(http_request, owned.agent_type)

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
        result, usage = await agent.resume(request.session_id, resume_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Resume Error: {str(e)}")

    balance = await charge_usage(db, current_user, usage, request.session_id)
    return await _to_response(
        result, request.session_id, balance if settings.ENABLE_BILLING else None
    )
