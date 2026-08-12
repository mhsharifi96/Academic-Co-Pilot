"""
Business logic for admin-authored guided workflows ("wizards").

Split into two layers, like ``app/services/download_service.py``:

* **Pure functions** (``apply_turn``, ``next_step_id``, ``reordered_positions``,
  ``resolve_locale``, ``localized``, ``slugify``, ``build_step_guidance``) hold
  the step state machine and the localisation rules. They take plain values —
  no DB, no clock — so they are unit-tested offline (``tests/test_wizard.py``).
* **DB wrappers** query Postgres via the async session and delegate the actual
  decisions to the pure functions. They follow the ``session_service.py``
  conventions: ``(db, user, ...)`` first args, self-committing, ``None`` for
  not-found (the endpoint turns that into a 404).

The run's conversation is driven by the shared ``AcademicAgent``; the current
step's ``guideline_prompt`` reaches the model through the per-turn
``context_message`` channel (``app/agents/base.py``), never through a rebuilt
system prompt.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.wizard import (
    DEFAULT_LANGUAGE,
    LANGUAGES,
    RESUMABLE_STATUSES,
    ROLE_ASSISTANT,
    ROLE_USER,
    STATUS_ABANDONED,
    STATUS_ACTIVE,
    STATUS_COMPLETED,
    WIZARD_AGENT_TYPE,
    Wizard,
    WizardMessage,
    WizardRun,
    WizardStep,
)
from app.services.session_service import ensure_session


class WizardHasNoSteps(Exception):
    """A wizard cannot be run until an admin has given it at least one step."""


class WizardInUse(Exception):
    """A destructive admin edit was refused because runs depend on the row."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Pure helpers — localisation
# --------------------------------------------------------------------------- #
def resolve_locale(lang: Optional[str]) -> str:
    """Normalise a requested language to one of ``LANGUAGES`` (default ``en``)."""
    code = (lang or "").strip().lower().replace("_", "-").split("-")[0]
    return code if code in LANGUAGES else DEFAULT_LANGUAGE


def localized(row: Any, field: str, lang: str) -> str:
    """
    Read ``<field>_<lang>`` off ``row``, falling back to the other language.

    Admins can publish a wizard with only one language filled in; showing the
    other language's text beats showing an empty card.
    """
    primary = (getattr(row, f"{field}_{lang}", "") or "").strip()
    if primary:
        return primary
    for other in LANGUAGES:
        if other == lang:
            continue
        alt = (getattr(row, f"{field}_{other}", "") or "").strip()
        if alt:
            return alt
    return ""


def slugify(raw: str) -> str:
    """
    ``"My New Wizard!"`` -> ``"my-new-wizard"``.

    Non-ASCII (e.g. Farsi) is stripped, so a Farsi-only input yields ``""`` —
    callers must reject that with a 400 rather than storing an empty slug.
    """
    text = unicodedata.normalize("NFKD", raw or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# --------------------------------------------------------------------------- #
# Pure helpers — bulk step authoring
# --------------------------------------------------------------------------- #
# An admin usually knows the shape of a workflow ("screen, ingest, plan, draft")
# before they know what each step should say. ``parse_step_outline`` turns that
# outline into step rows in one action; the guideline prompts are placeholders
# the admin refines afterwards in the editor.
MAX_OUTLINE_STEPS = 50

# ``{name}`` is substituted with the step's name. Deliberately generic: it must
# read as a prompt that still needs writing, not as a finished one.
DEFAULT_GUIDELINE_TEMPLATE = (
    "Guide the user through this step of the workflow: {name}. "
    "Stay on this step until its goal is met."
)

# Leading list markers people paste from a document: "1.", "2)", "-", "*", "•".
_OUTLINE_MARKER = re.compile(r"^\s*(?:\d+\s*[.)\]]|[-*•–—])\s*")


def parse_step_outline(
    outline: str,
    *,
    guideline_template: str = "",
    max_messages: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Turn a pasted outline into ``create_step`` keyword dicts, in order.

    One step per line. Blank lines are skipped and list markers are stripped, so
    a numbered list pasted from a document works as-is. A line may name the step
    in both languages by splitting on ``|`` (``English | فارسی``); with one side
    only, that text is used for both — ``localized`` would fall back to it
    anyway, and it keeps the editor's two name fields populated.

    ``guideline_template`` (``{name}`` substituted) fills the required
    ``guideline_prompt``; blank means ``DEFAULT_GUIDELINE_TEMPLATE``.

    Raises ``ValueError`` if nothing usable is left or there are more than
    ``MAX_OUTLINE_STEPS`` lines — both are 400s, not silent truncation.
    """
    template = (guideline_template or "").strip() or DEFAULT_GUIDELINE_TEMPLATE

    specs: List[Dict[str, Any]] = []
    for raw_line in (outline or "").splitlines():
        line = _OUTLINE_MARKER.sub("", raw_line).strip()
        if not line:
            continue
        english, _, farsi = line.partition("|")
        name_en = english.strip()
        name_fa = farsi.strip()
        # One-sided input names the step in both columns rather than leaving a
        # blank the admin has to notice later.
        name_en = name_en or name_fa
        name_fa = name_fa or name_en
        specs.append(
            {
                "name_en": name_en,
                "name_fa": name_fa,
                # ``str.format`` would blow up on any other brace in the text.
                "guideline_prompt": template.replace("{name}", name_en),
                "max_messages": max_messages,
            }
        )

    if not specs:
        raise ValueError("The outline has no steps — write one step per line.")
    if len(specs) > MAX_OUTLINE_STEPS:
        raise ValueError(
            f"Too many steps: {len(specs)} (the limit is {MAX_OUTLINE_STEPS})."
        )
    return specs


# --------------------------------------------------------------------------- #
# Pure helpers — step ordering
# --------------------------------------------------------------------------- #
def _sort_key(step: Any):
    # ``created_at`` then ``id`` break ties deterministically when an admin has
    # left two steps on the same position.
    return (step.position, step.created_at or datetime.min, step.id)


def ordered_steps(steps: Sequence[Any]) -> List[Any]:
    """Steps in execution order."""
    return sorted(steps, key=_sort_key)


def ordered_step_ids(steps: Sequence[Any]) -> List[str]:
    return [s.id for s in ordered_steps(steps)]


def step_number(steps: Sequence[Any], step_id: Optional[str]) -> Optional[int]:
    """1-based position of ``step_id`` in execution order, or ``None``."""
    if step_id is None:
        return None
    ids = ordered_step_ids(steps)
    return ids.index(step_id) + 1 if step_id in ids else None


def next_step_id(steps: Sequence[Any], current_step_id: Optional[str]) -> Optional[str]:
    """
    The id after ``current_step_id`` in execution order, or ``None`` if it is the
    last step.

    An unknown ``current_step_id`` (the step was deleted mid-run) also returns
    ``None``, so the run completes rather than jumping to an arbitrary step.
    """
    ids = ordered_step_ids(steps)
    if current_step_id not in ids:
        return None
    idx = ids.index(current_step_id)
    return ids[idx + 1] if idx + 1 < len(ids) else None


def reordered_positions(
    existing_ids: Sequence[str], requested_ids: Sequence[str]
) -> Dict[str, int]:
    """
    Map ``step_id -> new position`` for a reorder request.

    Raises ``ValueError`` unless ``requested_ids`` is a permutation of
    ``existing_ids`` — a partial reorder would silently corrupt the order.
    """
    if len(requested_ids) != len(set(requested_ids)):
        raise ValueError("Duplicate step ids in reorder request.")
    if set(requested_ids) != set(existing_ids):
        raise ValueError("Reorder request must list every step exactly once.")
    return {step_id: i for i, step_id in enumerate(requested_ids)}


# --------------------------------------------------------------------------- #
# Pure helpers — the step state machine
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class TurnOutcome:
    step_message_count: int  # new counter for the (possibly new) step
    new_current_step_id: Optional[str]  # None == leave current_step_id unchanged
    status: str  # STATUS_ACTIVE | STATUS_COMPLETED
    advanced: bool
    completed: bool


def messages_left(current_count: int, max_messages: Optional[int]) -> Optional[int]:
    """Turns remaining on the current step; ``None`` when the step is uncapped."""
    limit = max_messages if (max_messages or 0) > 0 else None
    if limit is None:
        return None
    return max(0, limit - current_count)


def apply_advance(*, next_step_id: Optional[str]) -> TurnOutcome:
    """
    Move to the next step regardless of the message cap.

    Drives the explicit "Finish step" action (and the agent's suggestion, once
    the user accepts it). The cap becomes a *ceiling* rather than the only way
    forward, which is what makes an uncapped step usable — it now ends when the
    work is done instead of parking the run forever.
    """
    if next_step_id is None:
        return TurnOutcome(0, None, STATUS_COMPLETED, False, True)
    return TurnOutcome(0, next_step_id, STATUS_ACTIVE, True, False)


def apply_turn(
    *,
    current_count: int,
    max_messages: Optional[int],
    next_step_id: Optional[str],
) -> TurnOutcome:
    """
    Decide what one *completed* user turn does to the run.

    Order of operations (deliberate):

    1. Count the turn that just happened: ``new_count = current_count + 1``.
    2. Compare against the cap with ``>=`` (not ``==``) so a cap an admin
       lowered mid-step still terminates instead of overshooting forever.
    3. Cap not reached -> stay on this step.
    4. Cap reached and there IS a next step -> advance, counter back to 0.
    5. Cap reached and this was the LAST step -> the run is completed.

    ``max_messages`` of ``None``, ``0`` or negative means **unlimited**. Reading
    ``0`` as "advance immediately" would make the step unreachable and stampede a
    whole wizard to completion inside one request; unlimited is the only safe
    reading of a value the admin API should never have accepted (it enforces
    ``ge=1``, so 0 can only arrive from hand-edited data).
    """
    new_count = current_count + 1
    limit = max_messages if (max_messages or 0) > 0 else None

    if limit is None or new_count < limit:
        return TurnOutcome(new_count, None, STATUS_ACTIVE, False, False)
    if next_step_id is None:
        return TurnOutcome(new_count, None, STATUS_COMPLETED, False, True)
    return TurnOutcome(0, next_step_id, STATUS_ACTIVE, True, False)


# --------------------------------------------------------------------------- #
# Pure helpers — the agent's "this step looks done" signal
# --------------------------------------------------------------------------- #
# The agent marks a step finished by emitting this token; the endpoint strips it
# before the reply is persisted or shown, and surfaces it as a flag so the UI can
# offer "Finish step". A text marker rather than a tool: the wizard runs on the
# shared agent, and a wizard-only tool would have to be hidden from every other
# caller of default_tools.
STEP_COMPLETE_MARKER = "[[STEP_COMPLETE]]"

# Tolerate the shapes models actually produce: different bracket counts, spacing,
# case, and a wrapping code fence or bold markers.
_MARKER_RE = re.compile(
    r"[`*_]*\[{1,2}\s*STEP[\s_-]*COMPLETE\s*\]{1,2}[`*_]*",
    re.IGNORECASE,
)


def extract_completion_signal(text: str) -> tuple[str, bool]:
    """
    Split an assistant reply into (clean_text, step_looks_complete).

    Returns the reply with every marker removed — the user must never see it —
    and whether at least one was present.
    """
    raw = text or ""
    if not _MARKER_RE.search(raw):
        return raw, False
    cleaned = _MARKER_RE.sub("", raw)
    # Collapse the blank lines the removal leaves behind.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, True


# --------------------------------------------------------------------------- #
# Pure helpers — suggested follow-up questions
# --------------------------------------------------------------------------- #
SUGGESTION_COUNT = 3

# Keep the prompt cheap: this runs on demand and is billed to the user, so only
# the tail of the conversation is sent and each message is clipped.
SUGGESTION_HISTORY_TURNS = 6
SUGGESTION_EXCERPT_CHARS = 700


@dataclass(frozen=True)
class Suggestion:
    question: str
    reason: str = ""


def build_suggestions_prompt(
    *,
    wizard_title: str,
    step_name: str,
    guideline_prompt: str,
    transcript: Sequence[Any],
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Build the user-side prompt asking a cheap model for follow-up questions.

    The questions are written **as the user**, in the first person, because the
    UI sends the chosen one verbatim as their next message.
    """
    recent = list(transcript)[-SUGGESTION_HISTORY_TURNS:]
    lines = []
    for m in recent:
        role = "User" if getattr(m, "role", "") == ROLE_USER else "Assistant"
        text = (getattr(m, "content", "") or "").strip()
        if len(text) > SUGGESTION_EXCERPT_CHARS:
            text = text[:SUGGESTION_EXCERPT_CHARS] + "…"
        if text:
            lines.append(f"{role}: {text}")
    convo = "\n\n".join(lines) if lines else "(the conversation has not started yet)"

    language = "Persian (Farsi)" if lang == "fa" else "English"
    return (
        f'The user is working through the "{wizard_title}" workflow.\n'
        f'They are on the step "{step_name}", whose goal is:\n'
        f"{guideline_prompt.strip()}\n\n"
        f"Conversation so far:\n{convo}\n\n"
        f"Propose exactly {SUGGESTION_COUNT} questions the USER could send next "
        f"to make progress on this step. Write each one in the first person, as "
        f"the user would type it, and in {language}. They must be specific to "
        f"this conversation — never generic filler — must not repeat something "
        f"already asked, and must be short enough to read at a glance. For each, "
        f"add one short sentence saying why it helps.\n\n"
        'Reply with ONLY a JSON array, no prose:\n'
        '[{"question": "...", "reason": "..."}, ...]'
    )


def parse_suggestions(raw: str) -> List[Suggestion]:
    """
    Parse the model's reply into at most ``SUGGESTION_COUNT`` suggestions.

    Tolerates code fences and surrounding prose, and drops malformed entries
    rather than failing the whole request — a partial list is still useful, and
    the caller treats an empty list as "no suggestions available".
    """
    text = (raw or "").strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []

    out: List[Suggestion] = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "") or "").strip()
        if not question:
            continue
        key = question.casefold()
        if key in seen:  # models sometimes repeat themselves
            continue
        seen.add(key)
        out.append(Suggestion(question=question, reason=str(item.get("reason", "") or "").strip()))
        if len(out) == SUGGESTION_COUNT:
            break
    return out


# --------------------------------------------------------------------------- #
# Pure helpers — the per-turn guidance injected as a SystemMessage
# --------------------------------------------------------------------------- #
def build_step_guidance(
    *,
    wizard_title: str,
    step_name: str,
    step_index: int,  # 1-based
    total_steps: int,
    guideline_prompt: str,
    remaining_messages: Optional[int],  # None == unlimited
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Build the wizard framing prepended to a turn's context message.

    Re-injected on *every* turn rather than once at step entry, for two reasons:
    it survives ``SummarizationMiddleware`` compressing the thread, and it lets
    the text explicitly retire the earlier steps' prompts — which are still
    sitting in the same LangGraph thread and would otherwise compete with the
    current step's instructions.
    """
    parts = [
        f'You are guiding the user through the "{wizard_title}" workflow.',
        f'This is step {step_index} of {total_steps}: "{step_name}".',
        "",
        "STEP INSTRUCTIONS — authoritative for this turn. Any workflow "
        "instructions earlier in this conversation belong to previous steps and "
        "are now obsolete; follow ONLY the instructions below:",
        guideline_prompt.strip(),
    ]
    if remaining_messages is not None:
        plural = "" if remaining_messages == 1 else "s"
        parts += [
            "",
            f"The user has {remaining_messages} message{plural} left in this "
            "step; the workflow then moves to the next step automatically. Do "
            "not announce step transitions yourself.",
        ]

    parts += [
        "",
        "WHEN THIS STEP IS DONE: if the goal above has been met and there is "
        f"nothing useful left to do here, append {STEP_COMPLETE_MARKER} as the "
        "very last thing in your reply. It is stripped before the user sees it "
        "— never mention it, never explain it, and never say the step is "
        "finished in your own words. Moving on is the user's choice: they get "
        "an option to continue, so do not act as if the next step has started. "
        "Omit the marker entirely while there is still work to do in this step.",
    ]

    if lang == "fa":
        parts += ["", "Respond in Persian (Farsi)."]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# DB — wizard reads
# --------------------------------------------------------------------------- #
async def list_published_wizards(db: AsyncSession) -> List[Wizard]:
    result = await db.execute(
        select(Wizard)
        .where(Wizard.is_published.is_(True))
        .order_by(Wizard.position, Wizard.created_at)
    )
    return list(result.scalars().all())


async def list_all_wizards(db: AsyncSession) -> List[Wizard]:
    result = await db.execute(select(Wizard).order_by(Wizard.position, Wizard.created_at))
    return list(result.scalars().all())


async def get_wizard(db: AsyncSession, wizard_id: str) -> Optional[Wizard]:
    return await db.get(Wizard, wizard_id)


async def get_wizard_by_slug(
    db: AsyncSession, slug: str, *, published_only: bool = True
) -> Optional[Wizard]:
    stmt = select(Wizard).where(Wizard.slug == slug)
    if published_only:
        stmt = stmt.where(Wizard.is_published.is_(True))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_steps(db: AsyncSession, wizard_id: str) -> List[WizardStep]:
    """A wizard's steps in execution order — the single source of that order."""
    result = await db.execute(
        select(WizardStep)
        .where(WizardStep.wizard_id == wizard_id)
        .order_by(WizardStep.position, WizardStep.created_at, WizardStep.id)
    )
    return list(result.scalars().all())


async def get_step(db: AsyncSession, step_id: str) -> Optional[WizardStep]:
    return await db.get(WizardStep, step_id)


async def count_steps_by_wizard(db: AsyncSession) -> Dict[str, int]:
    """``{wizard_id: step_count}`` — one query for the whole landing page."""
    result = await db.execute(
        select(WizardStep.wizard_id, func.count(WizardStep.id)).group_by(
            WizardStep.wizard_id
        )
    )
    return {row[0]: row[1] for row in result.all()}


# --------------------------------------------------------------------------- #
# DB — runs
# --------------------------------------------------------------------------- #
async def get_owned_run(
    db: AsyncSession, user: User, run_id: str
) -> Optional[WizardRun]:
    """Return the run iff it exists AND belongs to ``user``; else ``None``."""
    run = await db.get(WizardRun, run_id)
    if run is None or run.user_id != user.id:
        return None
    return run


async def _lock_run(db: AsyncSession, run_id: str) -> Optional[WizardRun]:
    """
    Re-read a run under ``SELECT ... FOR UPDATE``.

    Only ``record_turn`` uses this, and only for the moment it writes: the lock
    dies with the transaction, so taking it at the start of a turn would buy
    nothing (the transcript insert commits long before the agent replies) while
    pinning a pooled connection across a multi-second LLM call. Re-reading the
    counter here instead is what actually makes concurrent turns safe.
    """
    result = await db.execute(
        select(WizardRun).where(WizardRun.id == run_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def list_user_runs(
    db: AsyncSession, user: User, status: Optional[str] = None
) -> List[WizardRun]:
    stmt = select(WizardRun).where(WizardRun.user_id == user.id)
    if status:
        stmt = stmt.where(WizardRun.status == status)
    result = await db.execute(stmt.order_by(WizardRun.updated_at.desc()))
    return list(result.scalars().all())


async def list_run_messages(db: AsyncSession, run_id: str) -> List[WizardMessage]:
    result = await db.execute(
        select(WizardMessage)
        .where(WizardMessage.run_id == run_id)
        .order_by(WizardMessage.created_at, WizardMessage.id)
    )
    return list(result.scalars().all())


async def start_or_resume_run(
    db: AsyncSession, user: User, wizard: Wizard, *, title: Optional[str] = None
) -> WizardRun:
    """
    Return the user's existing *active* run for this wizard, or create one.

    Completed and abandoned runs are never reused: re-picking a finished wizard
    starts a fresh run on a fresh thread, leaving the old transcript intact.
    Creating a run also creates its backing ``ChatSession`` (``agent_type="wizard"``)
    so uploads, history and plan endpoints work on the thread.

    Raises ``WizardHasNoSteps`` if the wizard has no steps yet.
    """
    result = await db.execute(
        select(WizardRun)
        .where(
            WizardRun.user_id == user.id,
            WizardRun.wizard_id == wizard.id,
            WizardRun.status.in_(RESUMABLE_STATUSES),
        )
        .order_by(WizardRun.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    steps = await list_steps(db, wizard.id)
    if not steps:
        raise WizardHasNoSteps(f"Wizard '{wizard.slug}' has no steps yet.")

    run = WizardRun(
        user_id=user.id,
        wizard_id=wizard.id,
        current_step_id=steps[0].id,
        status=STATUS_ACTIVE,
        step_message_count=0,
    )
    db.add(run)
    await db.flush()  # populate run.session_id before the ChatSession row

    await ensure_session(
        db,
        user,
        run.session_id,
        title=(title or wizard.name)[:120],
        agent_type=WIZARD_AGENT_TYPE,
    )
    await db.commit()
    await db.refresh(run)
    return run


async def append_message(
    db: AsyncSession,
    run: WizardRun,
    step_id: Optional[str],
    role: str,
    content: str,
    *,
    commit: bool = True,
) -> WizardMessage:
    msg = WizardMessage(
        run_id=run.id, step_id=step_id, role=role, content=content or ""
    )
    db.add(msg)
    if commit:
        await db.commit()
        await db.refresh(msg)
    else:
        await db.flush()
    return msg


async def record_turn(
    db: AsyncSession, run: WizardRun, steps: Sequence[WizardStep]
) -> TurnOutcome:
    """
    Apply one completed turn to ``run``: bump the counter, advance the step or
    complete the run, and persist.

    The counter is re-read under a row lock rather than trusted from ``run``,
    which may have been loaded before the agent's reply — otherwise two turns
    that overlap would both increment from the same stale value and one would be
    lost. ``run`` is updated in place so the caller can build its response from
    it.
    """
    locked = await _lock_run(db, run.id)
    if locked is not None:
        run = locked

    current = next((s for s in steps if s.id == run.current_step_id), None)
    outcome = apply_turn(
        current_count=run.step_message_count,
        max_messages=current.max_messages if current is not None else None,
        next_step_id=next_step_id(steps, run.current_step_id),
    )

    run.step_message_count = outcome.step_message_count
    if outcome.new_current_step_id is not None:
        run.current_step_id = outcome.new_current_step_id
    run.status = outcome.status
    if outcome.completed:
        run.completed_at = _now()
    run.updated_at = _now()

    await db.commit()
    await db.refresh(run)
    return outcome


async def advance_run(
    db: AsyncSession, run: WizardRun, steps: Sequence[WizardStep]
) -> TurnOutcome:
    """
    Finish the current step now, ignoring its message cap.

    Backs the user's explicit "Finish step" action. Same locking rationale as
    ``record_turn``: the counter is re-read under the row lock so an advance
    racing an in-flight turn can't be computed from stale state.
    """
    locked = await _lock_run(db, run.id)
    if locked is not None:
        run = locked

    outcome = apply_advance(next_step_id=next_step_id(steps, run.current_step_id))

    run.step_message_count = outcome.step_message_count
    if outcome.new_current_step_id is not None:
        run.current_step_id = outcome.new_current_step_id
    run.status = outcome.status
    if outcome.completed:
        run.completed_at = _now()
    run.updated_at = _now()

    await db.commit()
    await db.refresh(run)
    return outcome


async def abandon_run(db: AsyncSession, user: User, run_id: str) -> bool:
    """Soft-delete a run, keeping its transcript and billing audit trail."""
    run = await get_owned_run(db, user, run_id)
    if run is None:
        return False
    run.status = STATUS_ABANDONED
    run.updated_at = _now()
    await db.commit()
    return True


async def count_runs_for_wizard(db: AsyncSession, wizard_id: str) -> int:
    result = await db.execute(
        select(func.count(WizardRun.id)).where(WizardRun.wizard_id == wizard_id)
    )
    return int(result.scalar_one() or 0)


async def count_active_runs_on_step(db: AsyncSession, step_id: str) -> int:
    result = await db.execute(
        select(func.count(WizardRun.id)).where(
            WizardRun.current_step_id == step_id,
            WizardRun.status == STATUS_ACTIVE,
        )
    )
    return int(result.scalar_one() or 0)


# --------------------------------------------------------------------------- #
# DB — admin CRUD
# --------------------------------------------------------------------------- #
async def slug_exists(
    db: AsyncSession, slug: str, *, exclude_id: Optional[str] = None
) -> bool:
    stmt = select(func.count(Wizard.id)).where(Wizard.slug == slug)
    if exclude_id:
        stmt = stmt.where(Wizard.id != exclude_id)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0) > 0


async def create_wizard(db: AsyncSession, **fields: Any) -> Wizard:
    wizard = Wizard(**fields)
    db.add(wizard)
    await db.commit()
    await db.refresh(wizard)
    return wizard


async def update_wizard(
    db: AsyncSession, wizard_id: str, **fields: Any
) -> Optional[Wizard]:
    wizard = await db.get(Wizard, wizard_id)
    if wizard is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(wizard, key, value)
    await db.commit()
    await db.refresh(wizard)
    return wizard


async def delete_wizard(db: AsyncSession, wizard_id: str) -> bool:
    """
    Delete a wizard that has never been run.

    Raises ``WizardInUse`` when any run exists: the ``ondelete="CASCADE"`` on
    ``wizard_runs`` would otherwise silently destroy users' transcripts. Admins
    should unpublish instead.
    """
    wizard = await db.get(Wizard, wizard_id)
    if wizard is None:
        return False
    if await count_runs_for_wizard(db, wizard_id) > 0:
        raise WizardInUse(
            "This wizard has runs; unpublish it instead of deleting it."
        )
    await db.delete(wizard)
    await db.commit()
    return True


async def _append_position(db: AsyncSession, wizard_id: str) -> int:
    """The position a step appended to ``wizard_id`` should take."""
    result = await db.execute(
        select(func.max(WizardStep.position)).where(WizardStep.wizard_id == wizard_id)
    )
    highest = result.scalar_one_or_none()
    return 0 if highest is None else int(highest) + 1


async def create_step(
    db: AsyncSession, wizard_id: str, **fields: Any
) -> Optional[WizardStep]:
    wizard = await db.get(Wizard, wizard_id)
    if wizard is None:
        return None
    if fields.get("position") is None:
        fields["position"] = await _append_position(db, wizard_id)
    step = WizardStep(wizard_id=wizard_id, **fields)
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def create_steps(
    db: AsyncSession, wizard_id: str, specs: Sequence[Dict[str, Any]]
) -> Optional[List[WizardStep]]:
    """
    Append several steps in one transaction, keeping the order given.

    All-or-nothing: one commit, so a wizard is never left with half an outline.
    Positions continue from the wizard's existing steps.
    """
    wizard = await db.get(Wizard, wizard_id)
    if wizard is None:
        return None
    position = await _append_position(db, wizard_id)
    created: List[WizardStep] = []
    for offset, spec in enumerate(specs):
        step = WizardStep(wizard_id=wizard_id, position=position + offset, **spec)
        db.add(step)
        created.append(step)
    await db.commit()
    for step in created:
        await db.refresh(step)
    return created


async def update_step(
    db: AsyncSession, step_id: str, **fields: Any
) -> Optional[WizardStep]:
    step = await db.get(WizardStep, step_id)
    if step is None:
        return None
    for key, value in fields.items():
        if value is not None:
            setattr(step, key, value)
    await db.commit()
    await db.refresh(step)
    return step


async def delete_step(db: AsyncSession, step_id: str) -> bool:
    """
    Delete a step no active run is sitting on.

    Raises ``WizardInUse`` otherwise: ``ondelete="SET NULL"`` would leave those
    runs with ``current_step_id = NULL``, and an unknown current step makes
    ``next_step_id`` return ``None`` — the run would quietly complete on its next
    turn.
    """
    step = await db.get(WizardStep, step_id)
    if step is None:
        return False
    if await count_active_runs_on_step(db, step_id) > 0:
        raise WizardInUse("An active run is currently on this step.")
    await db.delete(step)
    await db.commit()
    return True


async def reorder_steps(
    db: AsyncSession, wizard_id: str, step_ids: Sequence[str]
) -> Optional[List[WizardStep]]:
    """Rewrite every step's position. Raises ``ValueError`` on a non-permutation."""
    steps = await list_steps(db, wizard_id)
    if not steps:
        return None
    positions = reordered_positions([s.id for s in steps], step_ids)
    for step in steps:
        step.position = positions[step.id]
    await db.commit()
    return await list_steps(db, wizard_id)
