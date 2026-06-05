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
    """Holds uploaded file paths and pending-interrupt state for one session."""
    session_id: str
    files: List[str] = field(default_factory=list)
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
    # Synchronous wrapper for use inside LangChain @tool functions
    # (which run synchronously within the agent graph).
    # ------------------------------------------------------------------

    def sync_get_files(self, session_id: str) -> List[str]:
        """Synchronous wrapper around get_files()."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.get_files(session_id))

        # A loop is already running — run the coroutine in a separate thread
        # with its own loop so we don't deadlock on the asyncio.Lock.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, self.get_files(session_id))
            return future.result()


# Module-level singleton
session_manager = SessionManager()
