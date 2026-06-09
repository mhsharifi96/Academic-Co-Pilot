"""
Unit tests for the shared agent tool registry (app/agents/tools.py).

These guard the refactor that lets the academic and deep agents share one tool
list: the academic agent keeps the bespoke write_plan/update_plan planner, while
the deep agent omits them (deepagents supplies its own write_todos).  No network,
LLM, or deepagents install required.
"""

from app.agents.tools import default_tools


def _names(tools):
    return {t.name for t in tools}


def test_academic_includes_task_planner():
    names = _names(default_tools(include_task_planner=True))
    assert "write_plan" in names
    assert "update_plan" in names
    # A couple of core tools are always present.
    assert "screen_abstracts_csv" in names
    assert "draft_paper_section" in names


def test_deep_excludes_task_planner():
    names = _names(default_tools(include_task_planner=False))
    assert "write_plan" not in names
    assert "update_plan" not in names
    # Core tools survive.
    assert "search_my_papers" in names
    assert "compile_paper" in names


def test_deep_tools_are_a_strict_subset_of_academic():
    academic = _names(default_tools(include_task_planner=True))
    deep = _names(default_tools(include_task_planner=False))
    assert deep < academic
    assert academic - deep == {"write_plan", "update_plan"}


def test_default_tools_returns_fresh_list():
    """Each call returns an independent list (no shared mutable default)."""
    a = default_tools()
    b = default_tools()
    assert a is not b
    a.clear()
    assert b, "mutating one result must not affect another"
