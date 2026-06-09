import os
from typing import List, Optional
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain.agents.middleware import SummarizationMiddleware

from app.agents.base import BaseAgent
from app.agents.hitl import build_hitl_middleware
from app.core.config import settings
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
from app.tools.literature import search_literature, resolve_citation, search_scopus
from app.tools.exporter import compile_paper
from app.tools.task_planner import write_plan, update_plan


def _load_skills() -> str:
    skills_path = os.path.join(os.getcwd(), "skills.md")
    if os.path.exists(skills_path):
        with open(skills_path, "r") as f:
            return f.read()
    return "Skills details not found."


class AcademicAgent(BaseAgent):
    """
    The central agent for the PaperAgent system.

    Built on ``create_agent`` with:
      - a ``checkpointer`` (injected) for stateful, multi-turn chat that
        persists across requests — and, with the Postgres saver, across server
        restarts,
      - ``SummarizationMiddleware`` to compress long histories within the token
        budget,
      - ``HumanInTheLoopMiddleware`` to gate sensitive tools behind approval.

    The checkpointer is supplied by the application lifespan (``app/main.py``)
    so its lifecycle (e.g. the Postgres connection pool) is managed centrally.

    Available files for a session are injected per-request as a context message
    (see ``BaseAgent.run``), not baked into the static system prompt.
    """

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        if tools is None:
            tools = [
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
                compile_paper,
                write_plan,
                update_plan,
            ]

        self.skills_content = _load_skills()

        # A summarization LLM (cheap, deterministic) keeps long chats in budget.
        summarizer = SummarizationMiddleware(
            model=f"openai:{settings.OPENAI_MODEL}",
            trigger=("tokens", 4000),   # summarize once history exceeds ~4k tokens
            keep=("messages", 20),      # always retain the 20 most recent messages
        )

        middleware = [
            summarizer,
            build_hitl_middleware(),
        ]

        super().__init__(
            tools=tools,
            middleware=middleware,
            checkpointer=checkpointer,
        )

    def get_system_prompt(self) -> str:
        return (
            "You are an End-to-End Academic Co-Pilot. Your goal is to help "
            "researchers with literature screening, document ingestion, paper "
            "planning, RAG-based drafting, and data analytics.\n\n"
            "Here are the detailed skills and tools you have access to:\n"
            f"{self.skills_content}\n\n"
            "Important guidelines:\n"
            "- The list of files available in the current session is provided to "
            "you in a system message at the start of each turn. Use those paths "
            "when the user refers to their files.\n"
            "- Always call `get_csv_info` before writing analytics code for a CSV "
            "so you know the exact column names and data types.\n"
            "- To gather evidence, use `search_my_papers` (semantic search over "
            "already-ingested PDFs), `search_literature` (discover new papers on "
            "arXiv), `search_scopus` (peer-reviewed/indexed literature with "
            "citation counts, when configured), and `resolve_citation` (fetch "
            "clean citation metadata/BibTeX from a DOI or title). Use "
            "`summarize_paper` for a quick TL;DR of a single PDF without ingesting "
            "it. These are read-only and run without approval.\n"
            "- The tools `analytics_sandbox`, `screen_abstracts_csv`, `ingest_pdf`, "
            "`draft_paper_section`, and `compile_paper` require human approval "
            "before they run; proceed to call them when appropriate and the system "
            "will handle the approval step.\n"
            "- For any task that needs several steps or tool calls (roughly 3 or "
            "more), call `write_plan` FIRST to lay out the ordered steps, then call "
            "`update_plan` to mark each step `in_progress`/`done` as you go. Your "
            "current plan is shown back to you at the start of every turn, so it "
            "keeps you on track across summarization and approval pauses. These "
            "planning tools run without approval. Skip planning for simple "
            "one-or-two-step requests.\n\n"
            "Writing a full paper (section by section with approval):\n"
            "When the user asks you to write the full/whole paper, follow this "
            "protocol strictly:\n"
            "1. Ensure an outline exists. If you don't already have one, call "
            "`generate_paper_outline` first.\n"
            "2. Call `plan_paper_sections` on the outline to get the ordered list "
            "of section titles.\n"
            "3. Draft the sections ONE AT A TIME, in order, by calling "
            "`draft_paper_section` for each title — pass the full outline and the "
            "chosen citation style. Each call will PAUSE for the user's approval "
            "before it runs; that is expected. Wait for each section to be "
            "approved and drafted before moving to the next one. Do NOT batch "
            "multiple `draft_paper_section` calls at once.\n"
            "4. For empirical/data-driven sections (e.g. Methodology, Results), "
            "pass the relevant session CSV paths in `data_files` so the draft is "
            "grounded in the actual data. Omit `data_files` for narrative sections "
            "(e.g. Introduction, Conclusion).\n"
            "5. If the user rejects a section, adapt per their reason; if they "
            "edit the args, honor the edit. After every section is approved, "
            "present the assembled full paper in order. If the user wants a "
            "downloadable document, call `compile_paper` with the approved "
            "sections to produce a .docx (this also pauses for approval).\n\n"
            "- Always be professional, precise, and adhere to academic standards."
        )
