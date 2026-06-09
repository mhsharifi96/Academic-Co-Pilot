"""
Deep research agent built on the ``deepagents`` harness.

This is a SECOND, independent agent that runs alongside the existing
``AcademicAgent`` — it does not replace or modify it.  Where the academic agent
is a LangChain ``create_agent`` graph with optional human-in-the-loop approval,
this one is a ``deepagents.create_deep_agent`` graph that runs fully
autonomously:

  * **Planning** — ``deepagents`` injects a built-in ``write_todos`` planner, so
    the agent breaks a request into ordered steps on its own (surfaced to the UI
    via the session ``todos`` state; see ``app/api/v1/endpoints/sessions.py``).
  * **Memory** — a built-in thread-scoped virtual filesystem (``write_file`` /
    ``read_file``) plus the shared LangGraph checkpointer, so it remembers within
    a session and the conversation survives restarts / reloads.
  * **No HITL** — sensitive tools run without pausing for approval.

It shares the academic agent's tool set (minus the bespoke ``write_plan`` /
``update_plan`` tools, which ``write_todos`` supersedes) and the same checkpointer
instance, both supplied by the application lifespan (``app/main.py``).  Because it
sub-classes :class:`BaseAgent` and assigns the compiled graph to ``self.agent``,
the existing ``run`` / ``resume`` / ``aget_state`` plumbing works unchanged.
"""

import os
from typing import List, Optional
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.base import BaseAgent
from app.agents.tools import default_tools
from app.core.config import settings


def _load_skills() -> str:
    skills_path = os.path.join(os.getcwd(), "skills.md")
    if os.path.exists(skills_path):
        with open(skills_path, "r") as f:
            return f.read()
    return "Skills details not found."


class DeepResearchAgent(BaseAgent):
    """Autonomous deep-research agent (``deepagents.create_deep_agent``)."""

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        # Imported lazily so the rest of the app (and the offline test suite)
        # doesn't hard-require deepagents unless the deep agent is built.
        from deepagents import create_deep_agent

        if tools is None:
            # No write_plan/update_plan — deepagents supplies its own planner.
            tools = default_tools(include_task_planner=False)

        self.tools = tools
        self.skills_content = _load_skills()
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )

        # create_deep_agent returns a compiled LangGraph graph (ainvoke /
        # aget_state compatible).  The checkpointer is passed through so chat
        # state persists per thread_id, exactly like the academic agent.
        self.agent = create_deep_agent(
            model=self.llm,
            tools=tools,
            system_prompt=self.get_system_prompt(),
            checkpointer=checkpointer,
        )

    def get_system_prompt(self) -> str:
        return (
            "You are an autonomous, End-to-End Academic Co-Pilot operating in "
            "deep-research mode. Your goal is to help researchers with literature "
            "screening, document ingestion, paper planning, RAG-based drafting, "
            "and data analytics — carrying a task all the way to completion on "
            "your own.\n\n"
            "Here are the detailed skills and tools you have access to:\n"
            f"{self.skills_content}\n\n"
            "How you work:\n"
            "- Use your built-in `write_todos` planner to lay out the ordered "
            "steps for any multi-step task FIRST, then keep it updated "
            "(in_progress / completed) as you progress. This keeps you on track "
            "across long runs.\n"
            "- Use your built-in virtual filesystem (`write_file` / `read_file`) "
            "as working memory: stash intermediate notes, outlines, search "
            "results, and drafts so you can build on them later in the session.\n"
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
            "`summarize_paper` for a quick TL;DR of a single PDF without "
            "ingesting it.\n"
            "- You may call ANY tool directly, without asking for approval — "
            "including `analytics_sandbox`, `screen_abstracts_csv`, `ingest_pdf`, "
            "`draft_paper_section`, and `compile_paper`. Execute the user's whole "
            "request end to end and return the final result; do NOT stop mid-plan "
            "to ask the user to confirm individual steps.\n\n"
            "Writing a full paper (autonomous, section by section):\n"
            "When the user asks you to write the full/whole paper:\n"
            "1. Ensure an outline exists; call `generate_paper_outline` if not.\n"
            "2. Call `plan_paper_sections` on the outline to get the ordered list "
            "of section titles.\n"
            "3. Draft the sections ONE AT A TIME, in order, by calling "
            "`draft_paper_section` for each title — pass the full outline and the "
            "chosen citation style. Do them sequentially (not batched) so each "
            "builds on the last.\n"
            "4. For empirical/data-driven sections (e.g. Methodology, Results), "
            "pass the relevant session CSV paths in `data_files` so the draft is "
            "grounded in the actual data. Omit `data_files` for narrative "
            "sections (e.g. Introduction, Conclusion).\n"
            "5. After all sections are drafted, present the assembled full paper "
            "in order. If the user wants a downloadable document, call "
            "`compile_paper` to produce a .docx.\n\n"
            "- Always be professional, precise, and adhere to academic standards."
        )
