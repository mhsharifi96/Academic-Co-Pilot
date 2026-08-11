"""
Wizard endpoints: a public catalogue, authenticated runs, and admin CRUD.

A wizard is an ordered set of steps; each step injects its ``guideline_prompt``
into the agent for the turns spent on it, and reaching the step's
``max_messages`` cap advances the run (the last step's cap completes it). The
transcript is persisted in ``wizard_messages`` so a user can leave and continue.

Turns run on the shared ``AcademicAgent`` — the step prompt travels through the
per-turn context message, not through a rebuilt system prompt. See
``app/services/wizard_service.py`` for the state machine.

Language is chosen per request with ``?lang=en|fa``. Public and user routes
return text already resolved for that language; admin routes return the raw
``*_en``/``*_fa`` columns so both can be edited.
"""

import os
import shutil
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.context import build_session_context, final_text
from app.agents.guardrails import REFUSAL_MESSAGE, screen_message
from app.agents.hitl import build_resume_command_value, extract_interrupt
from app.api.schemas.wizard import (
    AbandonRunResponse,
    DeleteResponse,
    ReorderStepsRequest,
    StartRunRequest,
    StepAdminOut,
    StepCreate,
    StepUpdate,
    WizardAdminDetailOut,
    WizardAdminOut,
    WizardCreate,
    WizardMessageOut,
    WizardPublicDetailOut,
    WizardPublicOut,
    WizardResumeRequest,
    WizardRunDetailOut,
    WizardRunOut,
    WizardStepPublicOut,
    WizardTurnRequest,
    WizardTurnResponse,
    WizardUpdate,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_admin, get_current_user
from app.core.sessions import session_manager
from app.models.auth import User
from app.models.wizard import (
    ROLE_ASSISTANT,
    ROLE_USER,
    STATUS_ACTIVE,
    Wizard,
    WizardRun,
    WizardStep,
)
from app.services import wizard_service as svc
from app.services.billing_service import charge_usage, has_sufficient_balance

router = APIRouter()

LangQuery = Query(default="en", description="Content language: 'en' or 'fa'.")


# --------------------------------------------------------------------------- #
# Projection helpers
# --------------------------------------------------------------------------- #
def _get_agent(request: Request):
    """Wizards run on the shared academic agent."""
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent is not ready yet.")
    return agent


def _step_public(step: WizardStep, lang: str) -> WizardStepPublicOut:
    return WizardStepPublicOut(
        id=step.id,
        name=svc.localized(step, "name", lang),
        position=step.position,
        max_messages=step.max_messages,
    )


def _wizard_public(wizard: Wizard, step_count: int, lang: str) -> WizardPublicOut:
    return WizardPublicOut(
        id=wizard.id,
        slug=wizard.slug,
        title=svc.localized(wizard, "title", lang) or wizard.name,
        short_description=svc.localized(wizard, "short_description", lang),
        icon=wizard.icon,
        step_count=step_count,
        lang=lang,
    )


def _run_out(
    run: WizardRun,
    wizard: Wizard,
    steps: Sequence[WizardStep],
    lang: str,
) -> WizardRunOut:
    ordered = svc.ordered_steps(steps)
    current = next((s for s in ordered if s.id == run.current_step_id), None)
    return WizardRunOut(
        id=run.id,
        wizard_id=wizard.id,
        wizard_slug=wizard.slug,
        wizard_title=svc.localized(wizard, "title", lang) or wizard.name,
        session_id=run.session_id,
        status=run.status,
        current_step=_step_public(current, lang) if current else None,
        current_step_index=svc.step_number(ordered, run.current_step_id),
        total_steps=len(ordered),
        step_message_count=run.step_message_count,
        messages_left_in_step=(
            svc.messages_left(run.step_message_count, current.max_messages)
            if current
            else None
        ),
        created_at=run.created_at,
        updated_at=run.updated_at,
        completed_at=run.completed_at,
        lang=lang,
    )


async def _run_detail(
    db: AsyncSession,
    run: WizardRun,
    wizard: Wizard,
    steps: Sequence[WizardStep],
    lang: str,
) -> WizardRunDetailOut:
    base = _run_out(run, wizard, steps, lang)
    messages = await svc.list_run_messages(db, run.id)
    return WizardRunDetailOut(
        **base.model_dump(),
        steps=[_step_public(s, lang) for s in svc.ordered_steps(steps)],
        messages=[WizardMessageOut.model_validate(m) for m in messages],
    )


async def _load_run_context(
    db: AsyncSession, run: WizardRun
) -> tuple[Wizard, List[WizardStep]]:
    wizard = await svc.get_wizard(db, run.wizard_id)
    if wizard is None:
        # The CASCADE on wizard_runs makes this unreachable in practice.
        raise HTTPException(status_code=404, detail="Wizard not found.")
    steps = await svc.list_steps(db, wizard.id)
    return wizard, steps


# --------------------------------------------------------------------------- #
# Public catalogue (no authentication — this is the landing page)
# --------------------------------------------------------------------------- #
@router.get("/wizards", response_model=List[WizardPublicOut])
async def list_wizards(
    lang: str = LangQuery,
    db: AsyncSession = Depends(get_db),
) -> List[WizardPublicOut]:
    """Published wizards in display order. Callable without a token."""
    locale = svc.resolve_locale(lang)
    wizards = await svc.list_published_wizards(db)
    counts = await svc.count_steps_by_wizard(db)
    return [_wizard_public(w, counts.get(w.id, 0), locale) for w in wizards]


@router.get("/wizards/{slug}", response_model=WizardPublicDetailOut)
async def get_wizard_detail(
    slug: str,
    lang: str = LangQuery,
    db: AsyncSession = Depends(get_db),
) -> WizardPublicDetailOut:
    """One published wizard plus the shape of its path (step names and caps)."""
    locale = svc.resolve_locale(lang)
    wizard = await svc.get_wizard_by_slug(db, slug, published_only=True)
    if wizard is None:
        raise HTTPException(status_code=404, detail="Wizard not found.")
    steps = await svc.list_steps(db, wizard.id)
    base = _wizard_public(wizard, len(steps), locale)
    return WizardPublicDetailOut(
        **base.model_dump(), steps=[_step_public(s, locale) for s in steps]
    )


# --------------------------------------------------------------------------- #
# Runs
# --------------------------------------------------------------------------- #
@router.post("/wizard-runs", response_model=WizardRunDetailOut)
async def start_run(
    body: StartRunRequest,
    lang: str = LangQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WizardRunDetailOut:
    """
    Start a wizard, or resume the caller's existing active run of it.

    Returns the run *with* its transcript so "continue" needs only this one call.
    A completed or abandoned run is never reused — re-picking a finished wizard
    starts a fresh run on a fresh thread.
    """
    locale = svc.resolve_locale(lang)
    if bool(body.wizard_id) == bool(body.slug):
        raise HTTPException(
            status_code=400, detail="Provide exactly one of 'wizard_id' or 'slug'."
        )

    if body.wizard_id:
        wizard = await svc.get_wizard(db, body.wizard_id)
        if wizard is not None and not wizard.is_published:
            wizard = None
    else:
        wizard = await svc.get_wizard_by_slug(db, body.slug, published_only=True)
    if wizard is None:
        raise HTTPException(status_code=404, detail="Wizard not found.")

    try:
        run = await svc.start_or_resume_run(
            db,
            current_user,
            wizard,
            title=svc.localized(wizard, "title", locale) or wizard.name,
        )
    except svc.WizardHasNoSteps:
        raise HTTPException(
            status_code=409, detail="This wizard has no steps yet."
        )

    steps = await svc.list_steps(db, wizard.id)
    return await _run_detail(db, run, wizard, steps, locale)


@router.get("/wizard-runs", response_model=List[WizardRunOut])
async def list_runs(
    status: Optional[str] = Query(
        default=None, description="Filter by run status, e.g. 'active'."
    ),
    lang: str = LangQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WizardRunOut]:
    """The caller's runs, most recently active first."""
    locale = svc.resolve_locale(lang)
    runs = await svc.list_user_runs(db, current_user, status)

    out: List[WizardRunOut] = []
    wizards: Dict[str, Wizard] = {}
    steps_by_wizard: Dict[str, List[WizardStep]] = {}
    for run in runs:
        if run.wizard_id not in wizards:
            wizard = await svc.get_wizard(db, run.wizard_id)
            if wizard is None:
                continue
            wizards[run.wizard_id] = wizard
            steps_by_wizard[run.wizard_id] = await svc.list_steps(db, run.wizard_id)
        out.append(
            _run_out(
                run, wizards[run.wizard_id], steps_by_wizard[run.wizard_id], locale
            )
        )
    return out


@router.get("/wizard-runs/{run_id}", response_model=WizardRunDetailOut)
async def get_run(
    run_id: str,
    lang: str = LangQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WizardRunDetailOut:
    """A run the caller owns, with its full persisted transcript."""
    locale = svc.resolve_locale(lang)
    run = await svc.get_owned_run(db, current_user, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    wizard, steps = await _load_run_context(db, run)
    return await _run_detail(db, run, wizard, steps, locale)


def _turn_response(
    run: WizardRun,
    steps: Sequence[WizardStep],
    lang: str,
    *,
    response: str,
    status: str,
    interrupt: Optional[Dict[str, Any]] = None,
    outcome: Optional[svc.TurnOutcome] = None,
    balance: Optional[float] = None,
) -> WizardTurnResponse:
    ordered = svc.ordered_steps(steps)
    current = next((s for s in ordered if s.id == run.current_step_id), None)
    return WizardTurnResponse(
        response=response,
        run_id=run.id,
        session_id=run.session_id,
        status=status,
        interrupt=interrupt,
        run_status=run.status,
        step_advanced=bool(outcome and outcome.advanced),
        completed=bool(outcome and outcome.completed),
        current_step=_step_public(current, lang) if current else None,
        current_step_index=svc.step_number(ordered, run.current_step_id),
        total_steps=len(ordered),
        messages_left_in_step=(
            svc.messages_left(run.step_message_count, current.max_messages)
            if current
            else None
        ),
        balance=balance,
    )


@router.post("/wizard-runs/{run_id}/messages", response_model=WizardTurnResponse)
async def post_turn(
    run_id: str,
    body: WizardTurnRequest,
    http_request: Request,
    lang: str = LangQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WizardTurnResponse:
    """
    Take one turn in a run.

    The step advances *after* the agent has replied, so the assistant answers the
    user's Nth message with the step they were actually on — and both persisted
    rows carry that step.
    """
    locale = svc.resolve_locale(lang)
    run = await svc.get_owned_run(db, current_user, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status != STATUS_ACTIVE:
        raise HTTPException(
            status_code=409, detail=f"This run is {run.status} and cannot take turns."
        )

    wizard, steps = await _load_run_context(db, run)
    ordered = svc.ordered_steps(steps)
    current = next((s for s in ordered if s.id == run.current_step_id), None)
    if current is None:
        raise HTTPException(
            status_code=409,
            detail="This run's current step no longer exists; start the wizard again.",
        )

    # Guardrail before anything is spent or persisted. A refused turn must not
    # burn a step allowance, so nothing below this point runs.
    verdict = await screen_message(
        body.message, scope_check=wizard.enforce_scope_guardrail
    )
    if not verdict.allowed:
        return _turn_response(
            run,
            steps,
            locale,
            response=REFUSAL_MESSAGE,
            status="blocked",
            balance=current_user.balance if settings.ENABLE_BILLING else None,
        )

    if not has_sufficient_balance(current_user):
        raise HTTPException(
            status_code=402,
            detail=(
                "Your balance is exhausted. Please contact an administrator to "
                "top up your account before continuing."
            ),
        )

    await svc.append_message(db, run, current.id, ROLE_USER, body.message)
    await session_manager.get_or_create(run.session_id)

    guidance = svc.build_step_guidance(
        wizard_title=svc.localized(wizard, "title", locale) or wizard.name,
        step_name=svc.localized(current, "name", locale),
        step_index=svc.step_number(ordered, current.id) or 1,
        total_steps=len(ordered),
        guideline_prompt=current.guideline_prompt,
        remaining_messages=svc.messages_left(
            run.step_message_count, current.max_messages
        ),
        lang=locale,
    )
    context_message = "\n\n".join(
        [guidance, await build_session_context(run.session_id)]
    )

    agent = _get_agent(http_request)
    try:
        result, usage = await agent.run(
            body.message, session_id=run.session_id, context_message=context_message
        )
    except Exception as e:
        # The user's message row stays: the transcript should show the attempt.
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

    return await _finish_turn(
        db, current_user, run, wizard, steps, current, result, usage, locale
    )


async def _finish_turn(
    db: AsyncSession,
    user: User,
    run: WizardRun,
    wizard: Wizard,
    steps: Sequence[WizardStep],
    current: WizardStep,
    result: Any,
    usage: Dict[str, int],
    lang: str,
) -> WizardTurnResponse:
    """Persist the reply, bill the turn, and (unless paused) advance the step."""
    interrupt = extract_interrupt(result)

    def balance_of(value: Optional[float]) -> Optional[float]:
        return value if settings.ENABLE_BILLING else None

    if interrupt:
        # The turn isn't over — the graph is waiting on an approval. Record what
        # the user is being asked, but leave the counter alone; it advances when
        # the resume completes the turn.
        await session_manager.set_pending_interrupt(run.session_id, interrupt)
        await svc.append_message(
            db, run, current.id, ROLE_ASSISTANT, interrupt.get("message", "")
        )
        balance = await charge_usage(db, user, usage, run.session_id)
        return _turn_response(
            run,
            steps,
            lang,
            response=interrupt.get("message", ""),
            status="interrupted",
            interrupt=interrupt,
            balance=balance_of(balance),
        )

    await session_manager.set_pending_interrupt(run.session_id, None)
    reply = final_text(result)
    await svc.append_message(db, run, current.id, ROLE_ASSISTANT, reply)
    balance = await charge_usage(db, user, usage, run.session_id)
    outcome = await svc.record_turn(db, run, steps)
    return _turn_response(
        run,
        steps,
        lang,
        response=reply,
        status="complete",
        outcome=outcome,
        balance=balance_of(balance),
    )


@router.post("/wizard-runs/{run_id}/resume", response_model=WizardTurnResponse)
async def resume_run(
    run_id: str,
    body: WizardResumeRequest,
    http_request: Request,
    lang: str = LangQuery,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WizardTurnResponse:
    """
    Approve / edit / reject a tool call a wizard turn paused on.

    Only reachable when ``REQUIRE_TOOL_APPROVAL=true``. Completing the paused
    turn here is what finally advances the step counter.
    """
    locale = svc.resolve_locale(lang)
    run = await svc.get_owned_run(db, current_user, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status != STATUS_ACTIVE:
        raise HTTPException(
            status_code=409, detail=f"This run is {run.status} and cannot take turns."
        )

    pending = await session_manager.get_pending_interrupt(run.session_id)
    if not pending:
        raise HTTPException(
            status_code=409, detail="No tool call is awaiting approval for this run."
        )
    if body.decision == "edit" and not body.edited_args:
        raise HTTPException(
            status_code=400, detail="decision='edit' requires 'edited_args'."
        )

    wizard, steps = await _load_run_context(db, run)
    current = next((s for s in steps if s.id == run.current_step_id), None)
    if current is None:
        raise HTTPException(
            status_code=409,
            detail="This run's current step no longer exists; start the wizard again.",
        )

    resume_value = build_resume_command_value(
        decision=body.decision,
        edited_args=body.edited_args,
        reason=body.reason,
        pending_actions=pending.get("pending_actions"),
    )

    agent = _get_agent(http_request)
    try:
        result, usage = await agent.resume(run.session_id, resume_value)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Resume Error: {str(e)}")

    return await _finish_turn(
        db, current_user, run, wizard, steps, current, result, usage, locale
    )


@router.delete("/wizard-runs/{run_id}", response_model=AbandonRunResponse)
async def abandon_run(
    run_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AbandonRunResponse:
    """
    Abandon a run: drop its conversation thread and uploaded files, and mark the
    row abandoned. The transcript is kept — it is the record of what happened.
    """
    run = await svc.get_owned_run(db, current_user, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")

    saver = getattr(http_request.app.state, "checkpointer", None)
    if saver is not None and hasattr(saver, "adelete_thread"):
        try:
            await saver.adelete_thread(run.session_id)
        except Exception:
            pass  # best-effort: still clear files + mark the row below

    upload_dir = os.path.join("data", run.session_id)
    if os.path.isdir(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)
    await session_manager.remove(run.session_id)

    await svc.abandon_run(db, current_user, run_id)
    return AbandonRunResponse(run_id=run_id, abandoned=True)


# --------------------------------------------------------------------------- #
# Admin CRUD
# --------------------------------------------------------------------------- #
async def _wizard_admin_out(db: AsyncSession, wizard: Wizard) -> WizardAdminOut:
    steps = await svc.list_steps(db, wizard.id)
    return WizardAdminOut(
        **{
            k: getattr(wizard, k)
            for k in (
                "id",
                "slug",
                "name",
                "title_en",
                "title_fa",
                "short_description_en",
                "short_description_fa",
                "icon",
                "position",
                "is_published",
                "enforce_scope_guardrail",
                "created_at",
                "updated_at",
            )
        },
        step_count=len(steps),
        run_count=await svc.count_runs_for_wizard(db, wizard.id),
    )


@router.get("/admin/wizards", response_model=List[WizardAdminOut])
async def admin_list_wizards(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> List[WizardAdminOut]:
    """Every wizard, published or not, with both languages."""
    return [await _wizard_admin_out(db, w) for w in await svc.list_all_wizards(db)]


@router.get("/admin/wizards/{wizard_id}", response_model=WizardAdminDetailOut)
async def admin_get_wizard(
    wizard_id: str,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> WizardAdminDetailOut:
    wizard = await svc.get_wizard(db, wizard_id)
    if wizard is None:
        raise HTTPException(status_code=404, detail="Wizard not found.")
    base = await _wizard_admin_out(db, wizard)
    steps = await svc.list_steps(db, wizard_id)
    return WizardAdminDetailOut(
        **base.model_dump(), steps=[StepAdminOut.model_validate(s) for s in steps]
    )


@router.post("/admin/wizards", response_model=WizardAdminDetailOut, status_code=201)
async def admin_create_wizard(
    body: WizardCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> WizardAdminDetailOut:
    """Create a wizard. The slug defaults to a slugified ``name``."""
    slug = svc.slugify(body.slug or body.name)
    if not slug:
        raise HTTPException(
            status_code=400,
            detail=(
                "Could not derive a URL slug — provide 'slug' using latin "
                "letters, digits and hyphens."
            ),
        )
    if await svc.slug_exists(db, slug):
        raise HTTPException(status_code=409, detail=f"Slug '{slug}' is already taken.")

    fields = body.model_dump(exclude={"slug"})
    try:
        wizard = await svc.create_wizard(db, slug=slug, **fields)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Slug '{slug}' is already taken.")

    base = await _wizard_admin_out(db, wizard)
    return WizardAdminDetailOut(**base.model_dump(), steps=[])


@router.patch("/admin/wizards/{wizard_id}", response_model=WizardAdminDetailOut)
async def admin_update_wizard(
    wizard_id: str,
    body: WizardUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> WizardAdminDetailOut:
    fields = body.model_dump(exclude_unset=True)
    if "slug" in fields and fields["slug"] is not None:
        slug = svc.slugify(fields["slug"])
        if not slug:
            raise HTTPException(status_code=400, detail="Slug is empty after cleanup.")
        if await svc.slug_exists(db, slug, exclude_id=wizard_id):
            raise HTTPException(
                status_code=409, detail=f"Slug '{slug}' is already taken."
            )
        fields["slug"] = slug
    # Booleans must be settable to False, which update_wizard's None-skip allows
    # (only None is skipped), so no special-casing is needed here.
    wizard = await svc.update_wizard(db, wizard_id, **fields)
    if wizard is None:
        raise HTTPException(status_code=404, detail="Wizard not found.")

    base = await _wizard_admin_out(db, wizard)
    steps = await svc.list_steps(db, wizard_id)
    return WizardAdminDetailOut(
        **base.model_dump(), steps=[StepAdminOut.model_validate(s) for s in steps]
    )


@router.delete("/admin/wizards/{wizard_id}", response_model=DeleteResponse)
async def admin_delete_wizard(
    wizard_id: str,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    """Delete a wizard nobody has run. Refuses (409) once runs exist."""
    try:
        deleted = await svc.delete_wizard(db, wizard_id)
    except svc.WizardInUse as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Wizard not found.")
    return DeleteResponse(id=wizard_id, deleted=True)


@router.post(
    "/admin/wizards/{wizard_id}/steps", response_model=StepAdminOut, status_code=201
)
async def admin_create_step(
    wizard_id: str,
    body: StepCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> StepAdminOut:
    """Append a step (or insert at an explicit ``position``)."""
    step = await svc.create_step(db, wizard_id, **body.model_dump())
    if step is None:
        raise HTTPException(status_code=404, detail="Wizard not found.")
    return StepAdminOut.model_validate(step)


@router.patch("/admin/wizard-steps/{step_id}", response_model=StepAdminOut)
async def admin_update_step(
    step_id: str,
    body: StepUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> StepAdminOut:
    step = await svc.update_step(db, step_id, **body.model_dump(exclude_unset=True))
    if step is None:
        raise HTTPException(status_code=404, detail="Step not found.")
    return StepAdminOut.model_validate(step)


@router.delete("/admin/wizard-steps/{step_id}", response_model=DeleteResponse)
async def admin_delete_step(
    step_id: str,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DeleteResponse:
    """Delete a step no active run is sitting on. Refuses (409) otherwise."""
    try:
        deleted = await svc.delete_step(db, step_id)
    except svc.WizardInUse as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Step not found.")
    return DeleteResponse(id=step_id, deleted=True)


@router.put(
    "/admin/wizards/{wizard_id}/steps/reorder", response_model=List[StepAdminOut]
)
async def admin_reorder_steps(
    wizard_id: str,
    body: ReorderStepsRequest,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> List[StepAdminOut]:
    """Rewrite step order. ``step_ids`` must list every step exactly once."""
    try:
        steps = await svc.reorder_steps(db, wizard_id, body.step_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if steps is None:
        raise HTTPException(status_code=404, detail="Wizard has no steps.")
    return [StepAdminOut.model_validate(s) for s in steps]
