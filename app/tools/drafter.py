import os
from typing import List, Literal, Optional
import pandas as pd
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.db import get_vector_store
from app.core.config import settings

# Keep injected data summaries bounded so we don't blow the context window.
_MAX_DATA_CHARS = 2500


def _summarize_data_files(paths: List[str]) -> str:
    """
    Build a compact, bounded textual summary of one or more data files (CSV or
    Excel) for use as quantitative context when drafting empirical sections.

    For each file: shape, columns+dtypes, numeric describe(), and value_counts()
    for a 'decision' column when present (useful for screening results — the
    screener writes .xlsx, so Excel is supported alongside CSV).
    """
    blocks: List[str] = []
    for path in paths:
        if not path or not os.path.exists(path):
            blocks.append(f"[{path}]: (file not found — skipped)")
            continue
        lower = path.lower()
        try:
            if lower.endswith(".csv"):
                df = pd.read_csv(path)
            elif lower.endswith((".xlsx", ".xls")):
                df = pd.read_excel(path)
            else:
                # Unsupported data type — ignore silently.
                continue
        except Exception as e:
            blocks.append(f"[{path}]: (could not read data file: {e})")
            continue

        parts = [f"[{os.path.basename(path)}] — {df.shape[0]} rows × {df.shape[1]} cols"]
        parts.append("Columns: " + ", ".join(f"{c}({df[c].dtype})" for c in df.columns))

        numeric = df.select_dtypes(include="number")
        if not numeric.empty:
            parts.append("Numeric summary:\n" + numeric.describe().to_string())

        # Categorical highlights commonly useful for screening/result sections.
        for col in ("decision", "label", "category", "status"):
            if col in df.columns:
                counts = df[col].value_counts().head(10)
                parts.append(f"Value counts for '{col}':\n" + counts.to_string())
                break

        blocks.append("\n".join(parts))

    summary = "\n\n".join(blocks).strip()
    if len(summary) > _MAX_DATA_CHARS:
        summary = summary[:_MAX_DATA_CHARS] + "\n…(truncated)"
    return summary


@tool
def draft_paper_section(
    section_title: str,
    outline: str,
    citation_style: Literal["IEEE", "APA", "Vancouver"] = "IEEE",
    feedback: Optional[str] = None,
    data_files: Optional[List[str]] = None,
) -> str:
    """
    Drafts a specific section of an academic paper using RAG over ingested PDFs
    and a specified citation style. Optionally grounds the draft in quantitative
    data from uploaded CSV or Excel (.xlsx) files.

    Args:
        section_title: The title of the section to draft (e.g., 'Introduction').
        outline: The full paper outline for context.
        citation_style: The desired citation style (IEEE, APA, or Vancouver).
        feedback: Extra user considerations or specific points to cover.
        data_files: Optional list of data file paths (CSV or .xlsx) from the
            session whose data should inform this section. Pass relevant files
            for empirical sections (e.g. Results, Methodology) and omit them for
            purely narrative sections (e.g. Introduction).
    """
    vector_store = get_vector_store()
    # Search for context relevant to this section and the overall outline
    docs = vector_store.similarity_search(f"{section_title} in the context of {outline}", k=10)

    context = ""
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", f"Doc {i+1}")
        context += f"[{source}]: {doc.page_content}\n\n"

    data_summary = _summarize_data_files(data_files) if data_files else ""

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0.5)

    system_prompt = (
        f"You are a professional academic writer. Draft the section '{section_title}' "
        f"based on the provided outline and context. Use {citation_style} citation style. "
        "When citing, refer to the sources provided in the context using the [Source Name] format "
        "and then transform them into the requested style."
    )
    if data_summary:
        system_prompt += (
            " You are also given quantitative data summaries; when relevant, report "
            "concrete figures from this data accurately and do not invent numbers."
        )
    if feedback:
        system_prompt += f" Additional user feedback to incorporate: {feedback}"

    user_prompt = (
        f"Outline:\n{outline}\n\n"
        f"Section to Draft: {section_title}\n\n"
        f"Context from database:\n{context}"
    )
    if data_summary:
        user_prompt += f"\n\nQuantitative data available:\n{data_summary}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])

    return response.content
