from typing import Any, Dict, List, Optional, Sequence, Tuple
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.callbacks import get_usage_metadata_callback
from langgraph.types import Command
from langgraph.checkpoint.base import BaseCheckpointSaver
from app.core.config import settings


def _aggregate_usage(usage_metadata: Dict[str, Any]) -> Dict[str, int]:
    """
    Collapse the per-model usage dict returned by
    ``get_usage_metadata_callback`` into flat input/output token totals for
    this turn (summed across every model the turn happened to invoke).
    """
    input_tokens = output_tokens = 0
    for model_usage in (usage_metadata or {}).values():
        input_tokens += int(model_usage.get("input_tokens", 0) or 0)
        output_tokens += int(model_usage.get("output_tokens", 0) or 0)
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


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
    ) -> Tuple[Any, Dict[str, int]]:
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

        Returns
        -------
        (result, usage) : tuple
            ``result`` is the raw LangGraph state dict; ``usage`` is
            ``{"input_tokens", "output_tokens"}`` measured for *this* turn only
            (the callback scopes usage to this invocation, so the checkpointer
            replaying prior history does not inflate the count).
        """
        messages: list = []
        if context_message:
            messages.append(SystemMessage(content=context_message))
        messages.append(HumanMessage(content=message))

        with get_usage_metadata_callback() as cb:
            result = await self.agent.ainvoke(
                {"messages": messages},
                config=self._config(session_id),
            )
        return result, _aggregate_usage(cb.usage_metadata)

    async def resume(
        self, session_id: str, resume_value: Any
    ) -> Tuple[Any, Dict[str, int]]:
        """
        Resume a graph that is paused on a human-in-the-loop interrupt.

        ``resume_value`` is the payload expected by the interrupt — for HITL this
        is ``{"decisions": [...]}``. Returns ``(result, usage)`` like ``run``.
        """
        with get_usage_metadata_callback() as cb:
            result = await self.agent.ainvoke(
                Command(resume=resume_value),
                config=self._config(session_id),
            )
        return result, _aggregate_usage(cb.usage_metadata)
