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

from typing import Any, Dict, List

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
    "pending"). As you complete each step, call `update_plan` to mark progress.
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
def update_plan(step_index: int, status: str, config: RunnableConfig) -> str:
    """
    Update the status of one step in the current plan.

    Use this as you work: mark a step "in_progress" when you start it and "done"
    when it is finished, so the plan reflects real progress.

    Args:
        step_index: Zero-based index of the step (as shown in the rendered plan).
        status: New status — one of "in_progress" or "done" (or "pending" to reset).
    """
    session_id = _session_id(config)
    if not session_id:
        return "Error: no active session; cannot update the plan."
    if status not in ("pending", "in_progress", "done"):
        return f"Error: invalid status {status!r}. Use 'in_progress', 'done', or 'pending'."

    plan = session_manager.sync_get_plan(session_id)
    if not plan:
        return "There is no plan to update yet. Call `write_plan` first."
    if not (0 <= step_index < len(plan)):
        return f"Error: step_index {step_index} is out of range (plan has {len(plan)} steps)."

    session_manager.sync_update_plan_step(session_id, step_index, status)
    plan = session_manager.sync_get_plan(session_id)
    return "Plan updated:\n" + render_plan(plan)
