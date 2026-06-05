from pydantic import BaseModel
from typing import Any, Dict, Literal, Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # Auto-generated if not provided


class ResumeRequest(BaseModel):
    """Deliver a human decision for a tool call awaiting approval."""
    session_id: str
    decision: Literal["approve", "edit", "reject"]
    edited_args: Optional[Dict[str, Any]] = None  # required when decision == "edit"
    reason: Optional[str] = None                   # optional message when rejecting


class ChatResponse(BaseModel):
    response: str
    session_id: str
    status: Literal["complete", "interrupted"] = "complete"
    # Populated only when status == "interrupted": the tool(s) awaiting approval.
    interrupt: Optional[Dict[str, Any]] = None
    output: Optional[Any] = None
