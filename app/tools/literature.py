"""
External literature tools (read-only, network-backed).

  - ``search_literature`` searches arXiv (free, no API key) for papers matching
    a query.
  - ``resolve_citation`` resolves a DOI or title to clean citation metadata +
    a BibTeX entry via Crossref (free, no API key), so the agent can ground
    citations in real metadata instead of guessing.

The XML/JSON parsing is factored into pure helpers (``_parse_arxiv_atom`` /
``_format_crossref_work``) so it can be unit-tested offline. Network and parse
errors are caught and returned as strings — tools must never raise into the
LangGraph run.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List

import httpx
from langchain_core.tools import tool

_ARXIV_API = "http://export.arxiv.org/api/query"
_CROSSREF_API = "https://api.crossref.org/works"
# Crossref asks for a contact in the User-Agent / mailto for the "polite pool".
_POLITE_MAILTO = "paperagent@example.com"
_USER_AGENT = f"PaperAgent/1.0 (mailto:{_POLITE_MAILTO})"

_ATOM = "{http://www.w3.org/2005/Atom}"
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# arXiv
# --------------------------------------------------------------------------- #
def _parse_arxiv_atom(xml: str) -> List[Dict[str, str]]:
    """
    Parse an arXiv Atom feed into a list of {title, authors, year, id, link,
    summary} dicts. Pure (no network) so it can be tested offline.
    """
    root = ET.fromstring(xml)
    entries: List[Dict[str, str]] = []
    for entry in root.findall(f"{_ATOM}entry"):
        title = (entry.findtext(f"{_ATOM}title") or "").strip()
        summary = (entry.findtext(f"{_ATOM}summary") or "").strip()
        published = (entry.findtext(f"{_ATOM}published") or "").strip()
        link = (entry.findtext(f"{_ATOM}id") or "").strip()
        authors = [
            (a.findtext(f"{_ATOM}name") or "").strip()
            for a in entry.findall(f"{_ATOM}author")
        ]
        arxiv_id = link.rsplit("/abs/", 1)[-1] if "/abs/" in link else link
        entries.append({
            "title": " ".join(title.split()),
            "authors": ", ".join(a for a in authors if a),
            "year": published[:4],
            "id": arxiv_id,
            "link": link,
            "summary": " ".join(summary.split()),
        })
    return entries


@tool
def search_literature(query: str, max_results: int = 8) -> str:
    """
    Search arXiv for academic papers matching a query (free, no key required).

    Use this to discover relevant literature that has NOT been uploaded yet.
    Returns title, authors, year, arXiv id/link, and an abstract snippet for
    each hit. To then read or cite a paper, ingest its PDF or call
    `resolve_citation`.

    Args:
        query: Search terms (e.g. 'agentic RAG for legal compliance').
        max_results: Maximum number of papers to return (default 8).
    """
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max(1, min(max_results, 25)),
        "sortBy": "relevance",
    }
    try:
        resp = httpx.get(
            _ARXIV_API, params=params, timeout=20.0,
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        papers = _parse_arxiv_atom(resp.text)
    except Exception as e:
        return f"Error searching arXiv: {str(e)}"

    if not papers:
        return f"No arXiv papers found for {query!r}. Try broader or different terms."

    blocks = [f"Found {len(papers)} arXiv papers for {query!r}:\n"]
    for i, p in enumerate(papers, 1):
        snippet = p["summary"][:300] + ("…" if len(p["summary"]) > 300 else "")
        blocks.append(
            f"{i}. {p['title']} ({p['year']})\n"
            f"   Authors: {p['authors']}\n"
            f"   arXiv: {p['id']}  —  {p['link']}\n"
            f"   Abstract: {snippet}"
        )
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------- #
# Crossref
# --------------------------------------------------------------------------- #
def _bibtex_key(authors: List[str], year: str) -> str:
    """Build a simple BibTeX cite key like 'smith2023'."""
    first = authors[0].split()[-1].lower() if authors else "anon"
    first = re.sub(r"[^a-z0-9]", "", first) or "anon"
    return f"{first}{year or 'n.d.'}"


def _format_crossref_work(work: Dict) -> str:
    """
    Format a Crossref ``message`` work object into clean metadata + a BibTeX
    entry. Pure (no network) so it can be tested offline.
    """
    title = (work.get("title") or ["(untitled)"])[0]
    authors = [
        " ".join(p for p in (a.get("given"), a.get("family")) if p)
        for a in work.get("author", [])
    ]
    # year lives under issued/published date-parts
    date_parts = (
        work.get("issued", {}).get("date-parts")
        or work.get("published", {}).get("date-parts")
        or [[""]]
    )
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
    venue = (work.get("container-title") or [""])[0]
    doi = work.get("DOI", "")
    entry_type = "article" if work.get("type") == "journal-article" else "misc"

    bibtex_lines = [f"@{entry_type}{{{_bibtex_key(authors, year)},"]
    bibtex_lines.append(f"  title   = {{{title}}},")
    if authors:
        bibtex_lines.append(f"  author  = {{{' and '.join(authors)}}},")
    if year:
        bibtex_lines.append(f"  year    = {{{year}}},")
    if venue:
        bibtex_lines.append(f"  journal = {{{venue}}},")
    if doi:
        bibtex_lines.append(f"  doi     = {{{doi}}},")
    bibtex_lines.append("}")

    meta = [
        f"Title:   {title}",
        f"Authors: {', '.join(authors) if authors else '(unknown)'}",
        f"Year:    {year or '(unknown)'}",
        f"Venue:   {venue or '(unknown)'}",
        f"DOI:     {doi or '(none)'}",
        "",
        "BibTeX:",
        "\n".join(bibtex_lines),
    ]
    return "\n".join(meta)


@tool
def resolve_citation(doi_or_title: str) -> str:
    """
    Resolve a DOI or paper title to clean citation metadata and a BibTeX entry
    via Crossref (free, no key required).

    Use this to ground a citation in real metadata (authors, year, venue, DOI)
    instead of guessing. Pass a DOI when you have one for an exact match;
    otherwise pass the paper title for a best-match lookup.

    Args:
        doi_or_title: A DOI (e.g. '10.1145/3539618') or a paper title.
    """
    query = doi_or_title.strip()
    is_doi = bool(_DOI_RE.match(query)) or query.lower().startswith(("10.", "doi:"))
    headers = {"User-Agent": _USER_AGENT}
    try:
        if is_doi:
            doi = re.sub(r"^doi:", "", query, flags=re.IGNORECASE)
            resp = httpx.get(f"{_CROSSREF_API}/{doi}", timeout=20.0, headers=headers)
            resp.raise_for_status()
            work = resp.json()["message"]
        else:
            resp = httpx.get(
                _CROSSREF_API,
                params={"query.bibliographic": query, "rows": 1, "mailto": _POLITE_MAILTO},
                timeout=20.0, headers=headers,
            )
            resp.raise_for_status()
            items = resp.json()["message"].get("items", [])
            if not items:
                return f"No Crossref match found for {query!r}."
            work = items[0]
        return _format_crossref_work(work)
    except Exception as e:
        return f"Error resolving citation: {str(e)}"
