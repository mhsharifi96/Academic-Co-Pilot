"""Unit tests for the human-in-the-loop helpers (app/agents/hitl.py)."""

import pytest

from app.agents.hitl import (
    INTERRUPT_TOOLS,
    build_hitl_middleware,
    extract_interrupt,
    build_resume_command_value,
)


class _FakeInterrupt:
    """Mimics a langgraph Interrupt object (has a .value attribute)."""
    def __init__(self, value):
        self.value = value


def _interrupt_result(action_requests):
    return {"__interrupt__": [_FakeInterrupt({"action_requests": action_requests})]}


# --------------------------------------------------------------------------- #
# INTERRUPT_TOOLS / middleware
# --------------------------------------------------------------------------- #

def test_gated_tools_include_all_write_and_draft_tools():
    for tool in ("analytics_sandbox", "screen_abstracts_csv", "ingest_pdf",
                 "draft_paper_section"):
        assert tool in INTERRUPT_TOOLS


def test_build_hitl_middleware_gates_every_listed_tool():
    mw = build_hitl_middleware()
    # Every gated tool should be registered on the middleware.
    assert hasattr(mw, "interrupt_on")
    for tool in INTERRUPT_TOOLS:
        assert tool in mw.interrupt_on


# --------------------------------------------------------------------------- #
# extract_interrupt
# --------------------------------------------------------------------------- #

def test_extract_interrupt_returns_none_when_no_interrupt():
    assert extract_interrupt({"messages": []}) is None
    assert extract_interrupt({}) is None


def test_extract_interrupt_parses_pending_actions():
    result = _interrupt_result([
        {"name": "analytics_sandbox", "args": {"code": "print(1)"}, "description": "run code"},
    ])
    payload = extract_interrupt(result)
    assert payload is not None
    assert payload["pending_actions"] == [
        {"tool": "analytics_sandbox", "args": {"code": "print(1)"}, "description": "run code"}
    ]
    assert payload["allowed_decisions"] == ["approve", "edit", "reject"]
    assert "resume" in payload["message"].lower()


def test_extract_interrupt_handles_multiple_actions():
    result = _interrupt_result([
        {"name": "ingest_pdf", "args": {"file_path": "a.pdf"}},
        {"name": "ingest_pdf", "args": {"file_path": "b.pdf"}},
    ])
    payload = extract_interrupt(result)
    assert len(payload["pending_actions"]) == 2
    assert payload["pending_actions"][1]["args"]["file_path"] == "b.pdf"


# --------------------------------------------------------------------------- #
# build_resume_command_value
# --------------------------------------------------------------------------- #

def test_resume_approve_is_bare():
    val = build_resume_command_value(
        "approve", pending_actions=[{"tool": "analytics_sandbox", "args": {}}]
    )
    assert val == {"decisions": [{"type": "approve"}]}


def test_resume_reject_carries_reason():
    val = build_resume_command_value(
        "reject", reason="not now",
        pending_actions=[{"tool": "ingest_pdf", "args": {}}],
    )
    assert val == {"decisions": [{"type": "reject", "message": "not now"}]}


def test_resume_reject_without_reason_omits_message():
    val = build_resume_command_value(
        "reject", pending_actions=[{"tool": "ingest_pdf", "args": {}}]
    )
    assert val == {"decisions": [{"type": "reject"}]}


def test_resume_edit_preserves_tool_name_and_args():
    val = build_resume_command_value(
        "edit",
        edited_args={"section_title": "Results", "feedback": "be concise"},
        pending_actions=[{"tool": "draft_paper_section", "args": {}}],
    )
    decision = val["decisions"][0]
    assert decision["type"] == "edit"
    assert decision["edited_action"]["name"] == "draft_paper_section"
    assert decision["edited_action"]["args"]["section_title"] == "Results"


def test_resume_produces_one_decision_per_pending_action():
    val = build_resume_command_value(
        "approve",
        pending_actions=[
            {"tool": "ingest_pdf", "args": {}},
            {"tool": "ingest_pdf", "args": {}},
        ],
    )
    assert val["decisions"] == [{"type": "approve"}, {"type": "approve"}]


def test_resume_rejects_unknown_decision():
    with pytest.raises(ValueError):
        build_resume_command_value("maybe", pending_actions=[{"tool": "x", "args": {}}])
