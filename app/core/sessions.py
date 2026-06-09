"""
In-memory session manager for per-user file tracking and pending-interrupt state.

Conversation history is NOT stored here — that is owned by the LangGraph
checkpointer (keyed by thread_id == session_id).  This manager only tracks the
files a user has uploaded (which feed the agent's per-turn context message) and
remembers whether a session is currently paused awaiting human approval.
"""

import asyncio
import concurrent.futures
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Session:
    """Holds uploaded file paths, the task plan, and pending-interrupt state."""
    session_id: str
    files: List[str] = field(default_factory=list)
    # Ordered task checklist the agent writes for itself; each item is
    # {"text": str, "status": "pending" | "in_progress" | "done"}.  Lives here
    # (not in the message history) so it survives summarization and HITL pauses.
    plan: List[Dict[str, Any]] = field(default_factory=list)
    pending_interrupt: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SessionManager:
    """
    In-memory session store.  Lazily creates sessions on first access.
    All public async methods are serialised via an asyncio.Lock.
    """

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str) -> Session:
        """Return an existing session or create a new one."""
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = Session(session_id=session_id)
            return self._sessions[session_id]

    async def add_files(self, session_id: str, file_paths: List[str]) -> None:
        """Associate uploaded file paths with a session."""
        async with self._lock:
            session = self._sessions.setdefault(
                session_id, Session(session_id=session_id)
            )
            for path in file_paths:
                if path not in session.files:
                    session.files.append(path)

    async def get_files(self, session_id: str) -> List[str]:
        """Return the list of file paths for a session, or empty list if none."""
        async with self._lock:
            session = self._sessions.get(session_id)
            return list(session.files) if session else []

    async def remove(self, session_id: str) -> None:
        """Forget a session entirely (files + pending-interrupt state)."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def set_pending_interrupt(
        self, session_id: str, interrupt: Optional[Dict[str, Any]]
    ) -> None:
        """Record (or clear) the pending HITL interrupt for a session."""
        async with self._lock:
            session = self._sessions.setdefault(
                session_id, Session(session_id=session_id)
            )
            session.pending_interrupt = interrupt

    async def get_pending_interrupt(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return the pending HITL interrupt for a session, if any."""
        async with self._lock:
            session = self._sessions.get(session_id)
            return session.pending_interrupt if session else None

    # ------------------------------------------------------------------
    # Task plan (agent-authored multi-step checklist)
    # ------------------------------------------------------------------

    _VALID_STATUSES = ("pending", "in_progress", "done")

    async def get_plan(self, session_id: str) -> List[Dict[str, Any]]:
        """Return a copy of the session's task plan, or empty list if none."""
        async with self._lock:
            session = self._sessions.get(session_id)
            return [dict(item) for item in session.plan] if session else []

    async def set_plan(self, session_id: str, steps: List[str]) -> None:
        """Replace the session's plan with a fresh checklist (all pending)."""
        async with self._lock:
            session = self._sessions.setdefault(
                session_id, Session(session_id=session_id)
            )
            session.plan = [
                {"text": str(step), "status": "pending"}
                for step in steps
                if str(step).strip()
            ]

    async def update_plan_step(
        self, session_id: str, index: int, status: str
    ) -> None:
        """Set one plan step's status.  Out-of-range index / unknown status is a no-op."""
        if status not in self._VALID_STATUSES:
            return
        async with self._lock:
            session = self._sessions.get(session_id)
            if session and 0 <= index < len(session.plan):
                session.plan[index]["status"] = status

    # ------------------------------------------------------------------
    # Synchronous wrappers for use inside LangChain @tool functions
    # (which run synchronously within the agent graph).
    # ------------------------------------------------------------------

    @staticmethod
    def _run_sync(coro: Any) -> Any:
        """
        Run an async coroutine to completion from sync code.

        When no event loop is running we can use ``asyncio.run`` directly.  When
        a loop IS already running (the usual case inside the agent graph), run
        the coroutine in a separate thread with its own loop so we don't deadlock
        on the asyncio.Lock.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

    def sync_get_files(self, session_id: str) -> List[str]:
        """Synchronous wrapper around get_files()."""
        return self._run_sync(self.get_files(session_id))

    def sync_get_plan(self, session_id: str) -> List[Dict[str, Any]]:
        """Synchronous wrapper around get_plan()."""
        return self._run_sync(self.get_plan(session_id))

    def sync_set_plan(self, session_id: str, steps: List[str]) -> None:
        """Synchronous wrapper around set_plan()."""
        return self._run_sync(self.set_plan(session_id, steps))

    def sync_update_plan_step(
        self, session_id: str, index: int, status: str
    ) -> None:
        """Synchronous wrapper around update_plan_step()."""
        return self._run_sync(self.update_plan_step(session_id, index, status))


# Module-level singleton
session_manager = SessionManager()
