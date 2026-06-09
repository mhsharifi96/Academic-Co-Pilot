import os
from typing import List, Optional
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain.agents.middleware import SummarizationMiddleware

from app.agents.base import BaseAgent
from app.agents.hitl import build_hitl_middleware
from app.agents.tools import default_tools
from app.core.config import settings


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
            tools = default_tools(include_task_planner=True)

        self.skills_content = _load_skills()

        # A summarization LLM (cheap, deterministic) keeps long chats in budget.
        summarizer = SummarizationMiddleware(
            model=f"openai:{settings.OPENAI_MODEL}",
            trigger=("tokens", 4000),   # summarize once history exceeds ~4k tokens
            keep=("messages", 20),      # always retain the 20 most recent messages
        )

        middleware = [summarizer]
        # Only gate tools behind approval when REQUIRE_TOOL_APPROVAL is set;
        # otherwise the agent runs its whole plan and returns the final result.
        hitl = build_hitl_middleware()
        if hitl is not None:
            middleware.append(hitl)

        super().__init__(
            tools=tools,
            middleware=middleware,
            checkpointer=checkpointer,
        )

    def get_system_prompt(self) -> str:
        approval = settings.REQUIRE_TOOL_APPROVAL

        if approval:
            sensitive_tools = (
                "- The tools `analytics_sandbox`, `screen_abstracts_csv`, "
                "`ingest_pdf`, `draft_paper_section`, and `compile_paper` require "
                "human approval before they run; proceed to call them when "
                "appropriate and the system will handle the approval step.\n"
            )
            drafting = (
                "Writing a full paper (section by section with approval):\n"
                "When the user asks you to write the full/whole paper, follow this "
                "protocol strictly:\n"
                "1. Ensure an outline exists. If you don't already have one, call "
                "`generate_paper_outline` first.\n"
                "2. Call `plan_paper_sections` on the outline to get the ordered "
                "list of section titles.\n"
                "3. Draft the sections ONE AT A TIME, in order, by calling "
                "`draft_paper_section` for each title — pass the full outline and "
                "the chosen citation style. Each call will PAUSE for the user's "
                "approval before it runs; that is expected. Wait for each section "
                "to be approved and drafted before moving to the next one. Do NOT "
                "batch multiple `draft_paper_section` calls at once.\n"
                "4. For empirical/data-driven sections (e.g. Methodology, Results), "
                "pass the relevant session CSV paths in `data_files` so the draft "
                "is grounded in the actual data. Omit `data_files` for narrative "
                "sections (e.g. Introduction, Conclusion).\n"
                "5. If the user rejects a section, adapt per their reason; if they "
                "edit the args, honor the edit. After every section is approved, "
                "present the assembled full paper in order. If the user wants a "
                "downloadable document, call `compile_paper` with the approved "
                "sections to produce a .docx (this also pauses for approval).\n\n"
            )
        else:
            sensitive_tools = (
                "- You may call any tool — including `analytics_sandbox`, "
                "`screen_abstracts_csv`, `ingest_pdf`, `draft_paper_section`, and "
                "`compile_paper` — directly, without asking for approval. Execute "
                "the user's whole request end to end and return the final result; "
                "do NOT stop mid-plan to ask the user to confirm individual steps.\n"
            )
            drafting = (
                "Writing a full paper (autonomous, section by section):\n"
                "When the user asks you to write the full/whole paper, follow this "
                "protocol:\n"
                "1. Ensure an outline exists. If you don't already have one, call "
                "`generate_paper_outline` first.\n"
                "2. Call `plan_paper_sections` on the outline to get the ordered "
                "list of section titles.\n"
                "3. Draft the sections ONE AT A TIME, in order, by calling "
                "`draft_paper_section` for each title — pass the full outline and "
                "the chosen citation style. Draft every section without pausing for "
                "approval, but do them sequentially (one `draft_paper_section` call "
                "at a time, not batched) so each builds on the last.\n"
                "4. For empirical/data-driven sections (e.g. Methodology, Results), "
                "pass the relevant session CSV paths in `data_files` so the draft "
                "is grounded in the actual data. Omit `data_files` for narrative "
                "sections (e.g. Introduction, Conclusion).\n"
                "5. After all sections are drafted, present the assembled full "
                "paper in order. If the user wants a downloadable document, call "
                "`compile_paper` with the sections to produce a .docx.\n\n"
            )

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
            f"{sensitive_tools}"
            "- For any task that needs several steps or tool calls (roughly 3 or "
            "more), call `write_plan` FIRST to lay out the ordered steps, then call "
            "`update_plan` to mark each step `in_progress`/`done` as you go. Your "
            "current plan is shown back to you at the start of every turn, so it "
            "keeps you on track across summarization"
            f"{' and approval pauses' if approval else ''}. These "
            "planning tools run without approval. Skip planning for simple "
            "one-or-two-step requests.\n\n"
            f"{drafting}"
            "- Always be professional, precise, and adhere to academic standards."
        )
