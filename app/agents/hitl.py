"""
Human-in-the-loop (HITL) configuration and helpers.

Sensitive tools (those that execute code or write to disk / the DB) are gated
behind an approval interrupt.  When the agent wants to call one of these tools,
the LangGraph run pauses with an ``__interrupt__`` and waits for an approve /
edit / reject decision, which the API delivers via ``/chat/resume``.
"""

from typing import Any, Dict, List, Optional
from langchain.agents.middleware import HumanInTheLoopMiddleware

# Tools that require explicit human approval before execution.
# These either run arbitrary code, mutate persistent state, or produce content
# the researcher wants to sign off on before the agent proceeds.
#   - draft_paper_section is gated so the full-paper writing flow pauses for
#     approval BEFORE drafting each section (approve / edit args / reject).
INTERRUPT_TOOLS = [
    "analytics_sandbox",
    "screen_abstracts_csv",
    "ingest_pdf",
    "draft_paper_section",
]


def build_hitl_middleware() -> HumanInTheLoopMiddleware:
    """
    Build the HumanInTheLoopMiddleware that interrupts before any sensitive tool.

    ``True`` allows all decision types (approve, edit, reject, respond) for the
    gated tool.  Tools not listed are auto-approved and run without interruption.
    """
    interrupt_on: Dict[str, Any] = {name: True for name in INTERRUPT_TOOLS}
    return HumanInTheLoopMiddleware(
        interrupt_on=interrupt_on,
        description_prefix="⚠️  This tool requires your approval before running",
    )


def extract_interrupt(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Inspect a graph result for a pending HITL interrupt.

    Returns a JSON-serialisable payload describing the tool call(s) awaiting
    approval, or ``None`` if the run completed normally.

    The interrupt value is a ``HITLRequest`` dict containing ``action_requests``,
    each with ``name`` / ``args`` / ``description``.
    """
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None

    # __interrupt__ is a tuple/list of Interrupt objects; we use the first.
    interrupt_obj = interrupts[0]
    value = getattr(interrupt_obj, "value", interrupt_obj)

    action_requests = []
    if isinstance(value, dict):
        action_requests = value.get("action_requests", [])

    pending = [
        {
            "tool": ar.get("name"),
            "args": ar.get("args", {}),
            "description": ar.get("description", ""),
        }
        for ar in action_requests
    ]

    return {
        "pending_actions": pending,
        "allowed_decisions": ["approve", "edit", "reject"],
        "message": (
            "The agent wants to run a sensitive tool. "
            "Send your decision to POST /api/v1/chat/resume."
        ),
    }


def build_resume_command_value(
    decision: str,
    edited_args: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
    pending_actions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Translate an API decision into the ``Command(resume=...)`` payload expected
    by HumanInTheLoopMiddleware: ``{"decisions": [<decision>, ...]}``.

    One decision is produced per pending action.  ``edit`` / ``reject`` carry
    extra fields; ``approve`` is bare.
    """
    n = len(pending_actions) if pending_actions else 1
    decisions: List[Dict[str, Any]] = []

    for i in range(n):
        if decision == "approve":
            decisions.append({"type": "approve"})
        elif decision == "reject":
            d: Dict[str, Any] = {"type": "reject"}
            if reason:
                d["message"] = reason
            decisions.append(d)
        elif decision == "edit":
            # Edit applies to the (single) pending action; preserve its name.
            name = (
                pending_actions[i]["tool"]
                if pending_actions and i < len(pending_actions)
                else None
            )
            decisions.append({
                "type": "edit",
                "edited_action": {"name": name, "args": edited_args or {}},
            })
        else:
            raise ValueError(f"Unknown decision type: {decision!r}")

    return {"decisions": decisions}
