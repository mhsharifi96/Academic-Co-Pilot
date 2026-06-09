"""
Unit tests for the agent task planner (app/tools/task_planner.py) and the
SessionManager plan state that backs it.

Async methods are driven with asyncio.run so we need no async pytest plugin.
The tools are unwrapped with ``.func`` (the plain function under the @tool
decorator) and handed a fake run config carrying the session id.
"""

import asyncio

from app.core.sessions import SessionManager, session_manager
from app.tools import task_planner


def run(coro):
    return asyncio.run(coro)


def _cfg(session_id):
    return {"configurable": {"thread_id": session_id}}


# --------------------------------------------------------------------------- #
# SessionManager plan state
# --------------------------------------------------------------------------- #

def test_set_and_get_plan_marks_all_pending():
    sm = SessionManager()
    run(sm.set_plan("s1", ["search", "ingest", "draft"]))
    plan = run(sm.get_plan("s1"))
    assert [p["text"] for p in plan] == ["search", "ingest", "draft"]
    assert all(p["status"] == "pending" for p in plan)


def test_set_plan_drops_blank_steps():
    sm = SessionManager()
    run(sm.set_plan("s1", ["real step", "   ", ""]))
    plan = run(sm.get_plan("s1"))
    assert [p["text"] for p in plan] == ["real step"]


def test_get_plan_unknown_session_returns_empty():
    sm = SessionManager()
    assert run(sm.get_plan("nope")) == []


def test_get_plan_returns_a_copy():
    sm = SessionManager()
    run(sm.set_plan("s1", ["a"]))
    plan = run(sm.get_plan("s1"))
    plan[0]["status"] = "done"  # mutate the copy
    # internal state is untouched
    assert run(sm.get_plan("s1"))[0]["status"] == "pending"


def test_update_plan_step_sets_status():
    sm = SessionManager()
    run(sm.set_plan("s1", ["a", "b"]))
    run(sm.update_plan_step("s1", 1, "done"))
    assert run(sm.get_plan("s1"))[1]["status"] == "done"


def test_update_plan_step_out_of_range_is_noop():
    sm = SessionManager()
    run(sm.set_plan("s1", ["a"]))
    run(sm.update_plan_step("s1", 5, "done"))  # no IndexError
    assert run(sm.get_plan("s1"))[0]["status"] == "pending"


def test_update_plan_step_invalid_status_is_noop():
    sm = SessionManager()
    run(sm.set_plan("s1", ["a"]))
    run(sm.update_plan_step("s1", 0, "bogus"))
    assert run(sm.get_plan("s1"))[0]["status"] == "pending"


# --------------------------------------------------------------------------- #
# render_plan
# --------------------------------------------------------------------------- #

def test_render_plan_uses_status_marks():
    rendered = task_planner.render_plan([
        {"text": "one", "status": "done"},
        {"text": "two", "status": "in_progress"},
        {"text": "three", "status": "pending"},
    ])
    assert "[x] 0. one" in rendered
    assert "[~] 1. two" in rendered
    assert "[ ] 2. three" in rendered


def test_render_empty_plan():
    assert task_planner.render_plan([]) == "No plan yet."


# --------------------------------------------------------------------------- #
# write_plan / update_plan tools (use the module singleton, like real runs)
# --------------------------------------------------------------------------- #

def test_write_plan_tool_persists_to_session_manager():
    sid = "tool-write"
    out = task_planner.write_plan.func(
        steps=["search arxiv", "ingest top 2", "draft related work"],
        config=_cfg(sid),
    )
    assert "Plan saved" in out
    assert "[ ] 0. search arxiv" in out
    plan = run(session_manager.get_plan(sid))
    assert len(plan) == 3 and plan[0]["status"] == "pending"


def test_update_plan_tool_advances_step():
    sid = "tool-update"
    task_planner.write_plan.func(steps=["a", "b"], config=_cfg(sid))
    out = task_planner.update_plan.func(step_index=0, status="done", config=_cfg(sid))
    assert "[x] 0. a" in out
    assert run(session_manager.get_plan(sid))[0]["status"] == "done"


def test_update_plan_tool_out_of_range_message():
    sid = "tool-oor"
    task_planner.write_plan.func(steps=["only"], config=_cfg(sid))
    out = task_planner.update_plan.func(step_index=9, status="done", config=_cfg(sid))
    assert "out of range" in out


def test_update_plan_tool_without_plan():
    out = task_planner.update_plan.func(
        step_index=0, status="done", config=_cfg("tool-noplan")
    )
    assert "no plan" in out.lower()


def test_tools_require_session_id():
    assert "no active session" in task_planner.write_plan.func(
        steps=["x"], config={"configurable": {}}
    )
    assert "no active session" in task_planner.update_plan.func(
        step_index=0, status="done", config={}
    )
