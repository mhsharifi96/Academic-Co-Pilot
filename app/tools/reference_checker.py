"""
Reference checker tool.

``validate_references`` audits the reference list of a paper on two axes:

  1. **Links resolve** — every DOI / URL is dereferenced over the network so dead
     or fabricated links are flagged (deterministic, no LLM).
  2. **Citations are faithful** — a *powerful* model (``settings.POWERFUL_MODEL``,
     routed via ``app/repositories/llm.py``) checks that each reference is real
     and that the in-text claims citing it are actually supported — i.e. the agent
     did not hallucinate sources or attach a claim to the wrong paper.

The text-parsing helpers (``_find_references_section`` / ``_extract_references``)
are pure so they can be unit-tested offline; only ``_check_link`` and the LLM call
touch the network.
"""

import re
from typing import Dict, List, Optional

import httpx
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from app.repositories.llm import llm_repo

# DOIs and URLs anywhere in a line. DOI per Crossref's recommended pattern.
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>)\]}]+", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s\"'<>)\]}]+", re.IGNORECASE)
# Headings that introduce the reference list.
_REF_HEADING_RE = re.compile(
    r"^\s*#*\s*(references|bibliography|works cited|reference list)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Leading enumerators like "[12]" or "12." or "12)" that start a reference entry.
_ENUM_RE = re.compile(r"^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s+")

_MAX_PAPER_CHARS = 12000  # bound the LLM prompt
_MAX_REFS = 60            # don't fan out link checks unboundedly


def _find_references_section(text: str) -> str:
    """
    Return just the reference-list portion of ``text`` (everything after the last
    'References'/'Bibliography' heading), or the whole text if no heading is found.
    Pure (no network).
    """
    matches = list(_REF_HEADING_RE.finditer(text))
    if not matches:
        return text
    return text[matches[-1].end():]


def _split_reference_entries(block: str) -> List[str]:
    """
    Split a reference block into individual entries. Prefers explicit enumerators
    ([1], 1., 1)); falls back to non-empty lines. Pure (no network).
    """
    lines = [ln.rstrip() for ln in block.splitlines()]
    entries: List[str] = []
    current: List[str] = []
    saw_enum = False

    for line in lines:
        if _ENUM_RE.match(line):
            saw_enum = True
            if current:
                entries.append(" ".join(current).strip())
            current = [_ENUM_RE.sub("", line).strip()]
        elif line.strip():
            current.append(line.strip())
        else:
            if current:
                entries.append(" ".join(current).strip())
                current = []
    if current:
        entries.append(" ".join(current).strip())

    if not saw_enum:
        # No enumerators: treat each non-empty line as its own entry.
        entries = [ln.strip() for ln in lines if ln.strip()]
    return [e for e in entries if e]


def _extract_references(text: str, references: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Extract reference entries with any DOI / URL found in each. Pure (no network).

    ``references`` (if given) is treated as the reference block directly; otherwise
    the block is located inside ``text``.
    """
    block = references if references else _find_references_section(text)
    entries = _split_reference_entries(block)
    refs: List[Dict[str, str]] = []
    for i, raw in enumerate(entries[:_MAX_REFS], 1):
        doi_match = _DOI_RE.search(raw)
        url_match = _URL_RE.search(raw)
        doi = doi_match.group(0).rstrip(".,;") if doi_match else ""
        url = url_match.group(0).rstrip(".,;") if url_match else ""
        refs.append({"index": str(i), "raw": raw, "doi": doi, "url": url})
    return refs


def _check_link(client: httpx.Client, ref: Dict[str, str]) -> Dict[str, str]:
    """
    Resolve a reference's DOI/URL over the network. Returns a status dict. The
    function never raises — failures are reported as ``ok=False``.
    """
    target = f"https://doi.org/{ref['doi']}" if ref["doi"] else ref["url"]
    if not target:
        return {"ok": "", "status": "no-link", "final_url": ""}
    try:
        resp = client.head(target, follow_redirects=True, timeout=15.0)
        # Some servers reject HEAD; fall back to a lightweight GET.
        if resp.status_code >= 400:
            resp = client.get(target, follow_redirects=True, timeout=15.0)
        ok = resp.status_code < 400
        return {
            "ok": "yes" if ok else "no",
            "status": str(resp.status_code),
            "final_url": str(resp.url),
        }
    except Exception as e:
        return {"ok": "no", "status": f"error: {type(e).__name__}", "final_url": ""}


def _format_link_report(checked: List[Dict[str, str]]) -> str:
    """Render the deterministic link-check results. Pure (no network)."""
    lines = ["Link check (deterministic):"]
    for r in checked:
        link = (f"doi:{r['doi']}" if r["doi"] else r["url"]) or "(no link)"
        if r["ok"] == "yes":
            mark = "✓ resolves"
        elif r["ok"] == "no":
            mark = f"✗ broken ({r['status']})"
        else:
            mark = "— no link to check"
        lines.append(f"  [{r['index']}] {mark}  {link}")
    return "\n".join(lines)


def _build_llm_messages(paper_text: str, refs: List[Dict[str, str]]) -> List:
    """Assemble the powerful-model prompt for the semantic faithfulness check."""
    system = (
        "You are a meticulous academic reference auditor. You are given a paper's "
        "text and its numbered reference list (with automated link-resolution "
        "results). For EACH reference, assess:\n"
        "1. Plausibility: does the reference look like a real, correctly-formatted "
        "work (authors, year, venue), or possibly fabricated/garbled?\n"
        "2. Citation faithfulness: find where the paper cites this reference and "
        "judge whether the specific claim it supports is actually consistent with "
        "what this reference is about. Flag likely HALLUCINATIONS — claims attached "
        "to a source that would not support them, or citations that don't match "
        "the surrounding text.\n"
        "Be concrete and conservative: only flag a problem when there is real "
        "evidence for it. Output one short block per reference:\n"
        "  [n] VERDICT: OK | SUSPECT | LIKELY-HALLUCINATION — <one-line reason>\n"
        "End with a brief overall summary (how many OK / suspect / hallucinated)."
    )
    ref_lines = []
    for r in refs:
        link = (f"doi:{r['doi']}" if r["doi"] else r["url"]) or "(no link)"
        status = r.get("link_status", "")
        ref_lines.append(f"[{r['index']}] {r['raw']}  ({link}; link={status})")
    human = (
        "PAPER TEXT (may be truncated):\n"
        f"{paper_text[:_MAX_PAPER_CHARS]}\n\n"
        "REFERENCES:\n" + "\n".join(ref_lines)
    )
    return [SystemMessage(content=system), HumanMessage(content=human)]


@tool
def validate_references(paper_text: str, references: Optional[str] = None) -> str:
    """
    Validate the references used in a paper: that each link resolves AND that the
    in-text claims citing each reference are actually supported by it (catching
    hallucinated or mis-attributed citations).

    Runs two checks: (1) a deterministic network resolution of every DOI/URL, and
    (2) a faithfulness audit by a powerful model that compares the paper's claims
    against each reference. Use this before finalizing a paper, or to vet drafts
    produced by `draft_paper_section`.

    Args:
        paper_text: The paper (or section) text, INCLUDING its reference list. If
            the references live elsewhere, also pass them via `references`.
        references: Optional. The reference list as text, if not already contained
            in `paper_text`.
    """
    refs = _extract_references(paper_text, references)
    if not refs:
        return (
            "No references found. Provide the paper text including its "
            "References/Bibliography section, or pass the list via `references`."
        )

    # 1. Deterministic link resolution.
    with httpx.Client(headers={"User-Agent": "PaperAgent/1.0"}) as client:
        for r in refs:
            res = _check_link(client, r)
            r["link_status"] = (
                "resolves" if res["ok"] == "yes"
                else ("no-link" if res["ok"] == "" else f"broken/{res['status']}")
            )
    link_report = _format_link_report([
        {**r, "ok": "yes" if r["link_status"] == "resolves"
         else ("" if r["link_status"] == "no-link" else "no"),
         "status": r["link_status"]}
        for r in refs
    ])

    # 2. Semantic faithfulness via the powerful model.
    try:
        analysis = llm_repo.complete(
            _build_llm_messages(paper_text, refs),
            tier="powerful",
            temperature=0.1,
        )
    except Exception as e:
        analysis = f"(Semantic check unavailable: {type(e).__name__}: {e})"

    return (
        f"Reference validation — {len(refs)} reference(s) checked.\n\n"
        f"{link_report}\n\n"
        f"Faithfulness audit (model: {llm_repo.model_name('powerful')}):\n{analysis}"
    )
