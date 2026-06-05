from typing import List, Optional
from langchain_core.tools import BaseTool
from app.agents.base import BaseAgent
from app.tools.screener import screen_abstracts_csv


class ScreenerAgent(BaseAgent):
    """
    A focused agent that only screens academic literature.

    Built on the same ``create_agent`` foundation as ``AcademicAgent`` but with a
    single tool and no middleware/checkpointer by default (callers may supply
    them).
    """

    def __init__(self, tools: Optional[List[BaseTool]] = None):
        if tools is None:
            tools = [screen_abstracts_csv]
        super().__init__(tools)

    def get_system_prompt(self) -> str:
        return (
            "You are a helpful research assistant specializing in screening "
            "academic literature against inclusion/exclusion criteria."
        )
