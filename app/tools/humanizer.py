"""
Text humanizer tool.

``humanize_text`` rewrites text — typically AI-drafted prose — so it reads more
naturally and varied, reducing the tell-tale uniformity that AI-writing detectors
key on, while strictly preserving the meaning, facts, figures, and citations.

It uses the *powerful* model tier (``settings.POWERFUL_MODEL``) via the LLM
repository, since a stronger model produces noticeably more natural rewrites.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from app.repositories.llm import llm_repo

_SYSTEM = (
    "You are an expert academic editor. Rewrite the user's text so it reads as "
    "natural, fluent human writing with varied sentence length and rhythm, "
    "concrete phrasing, and smooth transitions — the kind of prose a careful human "
    "author produces. The goal is readable, authentic-sounding text that does not "
    "look mechanically generated.\n\n"
    "HARD CONSTRAINTS — do not violate:\n"
    "- Preserve the meaning, claims, facts, numbers, and technical accuracy exactly.\n"
    "- Keep every citation, reference marker, DOI, and quotation intact and in place.\n"
    "- Do not add new facts, sources, or claims; do not remove information.\n"
    "- Keep the requested tone and the original language.\n"
    "- Match roughly the original length.\n"
    "Return ONLY the rewritten text — no preamble, notes, or explanation."
)


@tool
def humanize_text(text: str, tone: str = "academic") -> str:
    """
    Rewrite text to read as natural, human-sounding prose (reducing AI-detection
    signals) WITHOUT changing its meaning, facts, numbers, or citations.

    Use this to polish AI-drafted sections so they read more naturally. It will
    not invent or drop information — citations and figures are preserved.

    Args:
        text: The text to humanize.
        tone: Desired tone/register (e.g. 'academic', 'formal', 'accessible').
            Defaults to 'academic'.
    """
    if not text or not text.strip():
        return "Nothing to humanize: `text` was empty."
    try:
        return llm_repo.complete(
            [
                SystemMessage(content=_SYSTEM + f"\nRequested tone: {tone}."),
                HumanMessage(content=text),
            ],
            tier="powerful",
            temperature=0.7,
        )
    except Exception as e:
        return f"Error humanizing text: {type(e).__name__}: {e}"
