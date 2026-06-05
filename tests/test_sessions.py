"""
Unit tests for the in-memory SessionManager (app/core/sessions.py).

Async methods are driven with asyncio.run so we need no async pytest plugin.
"""

import asyncio

from app.core.sessions import SessionManager


def run(coro):
    return asyncio.run(coro)


def test_get_or_create_is_idempotent():
    sm = SessionManager()
    s1 = run(sm.get_or_create("abc"))
    s2 = run(sm.get_or_create("abc"))
    assert s1 is s2
    assert s1.session_id == "abc"
    assert s1.files == []
    assert s1.pending_interrupt is None


def test_add_and_get_files_dedupes():
    sm = SessionManager()
    run(sm.add_files("s1", ["data/a.pdf", "data/b.csv"]))
    run(sm.add_files("s1", ["data/b.csv", "data/c.csv"]))  # b.csv repeated
    files = run(sm.get_files("s1"))
    assert files == ["data/a.pdf", "data/b.csv", "data/c.csv"]


def test_get_files_unknown_session_returns_empty():
    sm = SessionManager()
    assert run(sm.get_files("nope")) == []


def test_add_files_autocreates_session():
    sm = SessionManager()
    run(sm.add_files("fresh", ["x.csv"]))
    # session now exists with the file
    assert run(sm.get_files("fresh")) == ["x.csv"]


def test_pending_interrupt_roundtrip_and_clear():
    sm = SessionManager()
    payload = {"pending_actions": [{"tool": "ingest_pdf"}]}
    run(sm.set_pending_interrupt("s2", payload))
    assert run(sm.get_pending_interrupt("s2")) == payload
    run(sm.set_pending_interrupt("s2", None))
    assert run(sm.get_pending_interrupt("s2")) is None


def test_get_pending_interrupt_unknown_session_is_none():
    sm = SessionManager()
    assert run(sm.get_pending_interrupt("ghost")) is None


def test_sessions_are_isolated():
    sm = SessionManager()
    run(sm.add_files("a", ["a.csv"]))
    run(sm.add_files("b", ["b.csv"]))
    assert run(sm.get_files("a")) == ["a.csv"]
    assert run(sm.get_files("b")) == ["b.csv"]


def test_sync_get_files_outside_event_loop():
    sm = SessionManager()
    run(sm.add_files("s3", ["data/one.csv"]))
    # Called from a sync context (no running loop) — the asyncio.run branch.
    assert sm.sync_get_files("s3") == ["data/one.csv"]


def test_sync_get_files_inside_running_loop():
    """The thread-offload branch: sync_get_files called while a loop runs."""
    sm = SessionManager()
    run(sm.add_files("s4", ["data/two.csv"]))

    async def driver():
        # We're inside a running loop here; sync_get_files must not deadlock.
        return sm.sync_get_files("s4")

    assert run(driver()) == ["data/two.csv"]
