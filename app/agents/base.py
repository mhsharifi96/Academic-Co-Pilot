from typing import Any, List, Optional, Sequence
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command
from langgraph.checkpoint.base import BaseCheckpointSaver
from app.core.config import settings


class BaseAgent:
    """
    Base class for all agents, built on LangChain 1.0's ``create_agent``
    (a LangGraph state machine).

    State (full message history) is persisted by the ``checkpointer`` keyed by
    ``thread_id``, so callers pass only the new message each turn — the graph
    reloads prior context automatically.  Middleware (summarization,
    human-in-the-loop) is supplied by subclasses.
    """

    def __init__(
        self,
        tools: List[BaseTool],
        middleware: Sequence[Any] = (),
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        self.tools = tools
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        self.agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=self.get_system_prompt(),
            middleware=middleware,
            checkpointer=checkpointer,
        )

    def get_system_prompt(self) -> str:
        """Return the static system prompt string.  Override in subclasses."""
        raise NotImplementedError

    def _config(self, session_id: str) -> dict:
        """Build the per-thread invoke config for the checkpointer."""
        return {"configurable": {"thread_id": session_id}}

    async def run(
        self,
        message: str,
        session_id: str,
        context_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Run the agent for one turn.

        Parameters
        ----------
        message : str
            The new user message.
        session_id : str
            Used as the LangGraph ``thread_id`` for state persistence.
        context_message : str, optional
            Extra per-request context (e.g. the list of available files) injected
            as a SystemMessage ahead of the user message.  Not stored in the
            static system prompt because it changes between requests.
        """
        messages: list = []
        if context_message:
            messages.append(SystemMessage(content=context_message))
        messages.append(HumanMessage(content=message))

        return await self.agent.ainvoke(
            {"messages": messages},
            config=self._config(session_id),
        )

    async def resume(self, session_id: str, resume_value: Any) -> Any:
        """
        Resume a graph that is paused on a human-in-the-loop interrupt.

        ``resume_value`` is the payload expected by the interrupt — for HITL this
        is ``{"decisions": [...]}``.
        """
        return await self.agent.ainvoke(
            Command(resume=resume_value),
            config=self._config(session_id),
        )
