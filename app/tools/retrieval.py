"""
Read-only retrieval tools.

Two capabilities the agent previously lacked:
  - ``search_my_papers`` exposes a direct semantic search over the ingested
    corpus (the same ``similarity_search`` the planner/drafter use internally),
    so the agent can gather evidence without committing to a full draft.
  - ``summarize_paper`` produces a structured TL;DR of a single PDF.

Both are read-only and therefore NOT gated by HITL.
"""

import os
from typing import Optional

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader

from app.core.db import get_vector_store
from app.core.config import settings

# Bound how much PDF text we feed the summariser, mirroring the drafter's
# approach to keeping injected context within the token budget.
_MAX_SUMMARY_CHARS = 12000


def _bounded_text(text: str, limit: int = _MAX_SUMMARY_CHARS) -> str:
    """Return ``text`` truncated to ``limit`` chars with a visible marker."""
    text = (text or "").strip()
    if len(text) > limit:
        return text[:limit] + "\n…(truncated)"
    return text


@tool
def search_my_papers(query: str, k: int = 5) -> str:
    """
    Semantic search over the papers already ingested into the vector database.

    Use this to gather evidence or check what the ingested corpus says about a
    topic BEFORE drafting — it returns the most relevant passages without writing
    anything. For drafting a full section, use `draft_paper_section` instead.

    Args:
        query: What to look for (a question or topic).
        k: Number of passages to return (default 5).
    """
    try:
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(query, k=k)
    except Exception as e:
        return f"Error searching the corpus: {str(e)}"

    if not docs:
        return (
            "No relevant passages found. The corpus may be empty — ingest PDFs "
            "with `ingest_pdf` first, or try a broader query."
        )

    blocks = [f"Top {len(docs)} passages for: {query!r}\n"]
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", f"Doc {i}")
        page = doc.metadata.get("page")
        loc = f"{os.path.basename(str(source))}" + (f" p.{page + 1}" if isinstance(page, int) else "")
        snippet = doc.page_content.strip().replace("\n", " ")
        if len(snippet) > 500:
            snippet = snippet[:500] + "…"
        blocks.append(f"{i}. [{loc}] {snippet}")
    return "\n".join(blocks)


@tool
def summarize_paper(file_path: str, feedback: Optional[str] = None) -> str:
    """
    Produce a structured TL;DR of a single PDF paper: problem, method, data,
    key findings, and limitations.

    Use this to quickly understand an uploaded paper without ingesting it into
    the vector database.

    Args:
        file_path: Path to the PDF file (e.g. a session upload).
        feedback: Optional focus or extra considerations for the summary.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at '{file_path}'."

    try:
        documents = PyPDFLoader(file_path).load()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

    full_text = _bounded_text("\n".join(d.page_content for d in documents))
    if not full_text:
        return f"Error: No extractable text found in '{file_path}'."

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)

    system_prompt = (
        "You are an expert research assistant. Summarise the given academic paper "
        "concisely under these exact headings:\n"
        "- Problem\n- Method\n- Data\n- Key Findings\n- Limitations\n"
        "Be faithful to the text and do not invent results."
    )
    if feedback:
        system_prompt += f"\n\nAdditional focus from the user: {feedback}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Paper ({os.path.basename(file_path)}):\n\n{full_text}"),
    ])
    return response.content
