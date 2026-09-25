"""
Task-planning tools — a lightweight, agent-authored todo list.

For long, multi-step jobs the agent writes a checklist with ``write_plan`` and
ticks items off with ``update_plan``.  The plan is stored in ``SessionManager``
(NOT in the message history), so it survives ``SummarizationMiddleware``
compression and the HITL approval pauses — keeping the agent on track across a
whole task instead of losing the thread.

These tools are scratch memory, not code execution, so they are NOT gated behind
human approval (they are absent from ``INTERRUPT_TOOLS``).

The current ``session_id`` is read from the LangGraph run config
(``thread_id == session_id``) via an injected ``RunnableConfig`` — the model
never has to supply it.
"""

from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.core.sessions import session_manager

_STATUS_MARK = {"done": "[x]", "in_progress": "[~]", "pending": "[ ]"}


def _session_id(config: RunnableConfig) -> str:
    """Pull the session id (== LangGraph thread_id) out of the run config."""
    return ((config or {}).get("configurable") or {}).get("thread_id", "")


def render_plan(plan: List[Dict[str, Any]]) -> str:
    """Render a plan as a human-readable checklist."""
    if not plan:
        return "No plan yet."
    lines = []
    for i, item in enumerate(plan):
        mark = _STATUS_MARK.get(item.get("status", "pending"), "[ ]")
        lines.append(f"{mark} {i}. {item.get('text', '')}")
    return "\n".join(lines)


@tool
def write_plan(steps: List[str], config: RunnableConfig) -> str:
    """
    Record an ordered checklist of steps for a multi-step task.

    Call this FIRST whenever a request needs several steps or tool calls (roughly
    3 or more) — e.g. searching literature, then ingesting papers, then drafting.
    It replaces any existing plan with a fresh checklist (every step starts
    "pending"). As work completes steps, call `update_plan` to mark progress —
    batching several steps into one call.
    The current plan is shown back to you at the start of every turn, so it keeps
    you on track even across summarization and approval pauses.

    Args:
        steps: The ordered list of step descriptions (short, imperative phrases).
    """
    session_id = _session_id(config)
    if not session_id:
        return "Error: no active session; cannot save a plan."
    session_manager.sync_set_plan(session_id, steps)
    plan = session_manager.sync_get_plan(session_id)
    return "Plan saved:\n" + render_plan(plan)


@tool
def update_plan(
    status: str,
    config: RunnableConfig,
    step_index: Optional[int] = None,
    step_indices: Optional[List[int]] = None,
) -> str:
    """
    Update the status of one or more steps in the current plan.

    Call this only after real work finishes a step (or several) — not once per
    step in a row. Batch updates in ONE call with `step_indices`: e.g. after a
    search that covered steps 0-2, call `step_indices=[0, 1, 2], status="done"`.

    Args:
        status: New status — one of "in_progress" or "done" (or "pending" to reset).
        step_index: Zero-based index of a single step (as shown in the rendered plan).
        step_indices: Zero-based indices of several steps to set to `status` at once.
    """
    session_id = _session_id(config)
    if not session_id:
        return "Error: no active session; cannot update the plan."
    if status not in ("pending", "in_progress", "done"):
        return f"Error: invalid status {status!r}. Use 'in_progress', 'done', or 'pending'."

    indices = list(step_indices or [])
    if step_index is not None:
        indices.append(step_index)
    if not indices:
        return "Error: pass `step_index` or `step_indices`."

    plan = session_manager.sync_get_plan(session_id)
    if not plan:
        return "There is no plan to update yet. Call `write_plan` first."
    bad = [i for i in indices if not (0 <= i < len(plan))]
    if bad:
        return f"Error: step_index {bad[0]} is out of range (plan has {len(plan)} steps)."

    for i in dict.fromkeys(indices):
        session_manager.sync_update_plan_step(session_id, i, status)
    plan = session_manager.sync_get_plan(session_id)
    return "Plan updated:\n" + render_plan(plan)
