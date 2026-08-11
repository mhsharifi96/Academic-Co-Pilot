"""
Shared helpers for building an agent turn's inputs and reading its outputs.

The per-turn *context message* is how request-scoped facts reach the model: it
is prepended as a ``SystemMessage`` ahead of the user's turn
(``app/agents/base.py``) rather than baked into the static system prompt,
because the file set and plan change between requests. It is deliberately
filtered out of the ``/history`` projection, so it never shows up in a
transcript.

Both the plain chat endpoint and the wizard endpoint build their context here;
the wizard prepends its own step framing on top (see
``app/services/wizard_service.build_step_guidance``).
"""

from typing import Any, Dict

from langchain_core.messages import AIMessage

from app.core.sessions import session_manager
from app.tools.task_planner import render_plan


def final_text(result: Dict[str, Any]) -> str:
    """Extract the last AI message text from a graph result."""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


async def build_session_context(session_id: str) -> str:
    """
    Build the per-turn system context: session id, uploaded files, current plan.

    The ``session_id`` line is load-bearing — tools such as ``ingest_pdf`` read
    it out of context to know which session they are writing into.
    """
    parts = [f"Current session_id: {session_id}"]

    files = await session_manager.get_files(session_id)
    if not files:
        parts.append(
            "Session files: (none uploaded yet — the user can upload PDFs/CSVs)."
        )
    else:
        listed = "\n".join(f"  - {f}" for f in files)
        parts.append(f"Files available in this session:\n{listed}")

    plan = await session_manager.get_plan(session_id)
    if plan:
        parts.append(
            "Current task plan (update it with `update_plan` as you progress):\n"
            + render_plan(plan)
        )

    return "\n\n".join(parts)
