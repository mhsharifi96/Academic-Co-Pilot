"""
Checkpointer factory for conversation persistence.

Conversation history (the LangGraph message state) is owned by a checkpointer
keyed by ``thread_id == session_id``.  In production we use an
``AsyncPostgresSaver`` backed by the same Postgres instance as the vector store,
so sessions survive server restarts.  When ``DATABASE_URL`` is unset (e.g. unit
tests or a quick local run without a DB) we fall back to an in-memory saver.

The Postgres saver holds a live async connection pool, so it must be opened and
closed within the application lifespan (see ``app/main.py``).  This module only
builds the (not-yet-entered) context manager / fallback instance; lifecycle is
managed by the caller.
"""

from typing import Any
from langgraph.checkpoint.memory import InMemorySaver
from app.core.config import settings


def build_checkpointer_cm() -> Any:
    """
    Return an async context manager yielding the conversation checkpointer.

    - With ``DATABASE_URL`` set → an ``AsyncPostgresSaver`` context manager.
      The caller must ``async with`` it and call ``.setup()`` once on the
      yielded saver to create the checkpoint tables.
    - Without it → a trivial async CM yielding an ``InMemorySaver`` (no setup
      needed; ``.setup()`` is a harmless no-op we provide).
    """
    db_url = getattr(settings, "DATABASE_URL", None)
    if db_url:
        # Imported lazily so the package isn't required when running with the
        # in-memory fallback (e.g. the unit-test suite).
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        return AsyncPostgresSaver.from_conn_string(db_url)

    return _InMemoryCM()


class _InMemoryCM:
    """Async-context-manager wrapper around InMemorySaver for the no-DB path."""

    def __init__(self) -> None:
        self._saver = InMemorySaver()

    async def __aenter__(self) -> InMemorySaver:
        # InMemorySaver has no async setup; expose a no-op so the lifespan can
        # call ``await saver.setup()`` uniformly regardless of backend.
        if not hasattr(self._saver, "setup"):
            async def _noop() -> None:
                return None

            self._saver.setup = _noop  # type: ignore[attr-defined]
        return self._saver

    async def __aexit__(self, *exc: Any) -> None:
        return None
