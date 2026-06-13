"""
Shared tool registry for the agents.

Both the ``AcademicAgent`` (LangChain ``create_agent``) and the
``DeepResearchAgent`` (``deepagents.create_deep_agent``) draw their tool set from
here so the two agents stay in sync.  The deep agent skips the bespoke
``write_plan`` / ``update_plan`` planning tools because ``deepagents`` injects its
own ``write_todos`` planner.
"""

from typing import List
from langchain_core.tools import BaseTool

from app.tools.screener import screen_abstracts_csv
from app.tools.ingestor import ingest_pdf
from app.tools.planner import (
    suggest_paper_titles,
    generate_paper_outline,
    plan_paper_sections,
)
from app.tools.drafter import draft_paper_section
from app.tools.sandbox import analytics_sandbox
from app.tools.file_utils import get_csv_info, list_session_files
from app.tools.retrieval import search_my_papers, summarize_paper
from app.tools.literature import (
    search_literature,
    resolve_citation,
    search_scopus,
    search_openalex,
)
from app.tools.exporter import compile_paper
from app.tools.reference_checker import validate_references
from app.tools.humanizer import humanize_text
from app.tools.infographic import generate_infographic
from app.tools.venue_suggester import suggest_venues
from app.tools.task_planner import write_plan, update_plan


# Tools every agent shares (everything except the bespoke planning tools).
_CORE_TOOLS: List[BaseTool] = [
    screen_abstracts_csv,
    ingest_pdf,
    suggest_paper_titles,
    generate_paper_outline,
    plan_paper_sections,
    draft_paper_section,
    analytics_sandbox,
    get_csv_info,
    list_session_files,
    search_my_papers,
    summarize_paper,
    search_literature,
    resolve_citation,
    search_scopus,
    search_openalex,
    compile_paper,
    validate_references,
    humanize_text,
    generate_infographic,
    suggest_venues,
]


def default_tools(include_task_planner: bool = True) -> List[BaseTool]:
    """
    Return the tool list for an agent.

    ``include_task_planner`` adds the ``write_plan`` / ``update_plan`` tools used
    by the academic agent.  The deep agent omits them (``False``) because
    ``deepagents`` provides an equivalent built-in ``write_todos`` planner.
    """
    tools = list(_CORE_TOOLS)
    if include_task_planner:
        tools += [write_plan, update_plan]
    return tools
