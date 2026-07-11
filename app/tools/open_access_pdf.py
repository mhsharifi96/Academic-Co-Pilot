"""
Find, download, ingest, and attach an open-access PDF to the current session.

This is intentionally conservative: it searches open metadata (OpenAlex), tries
only candidate open-access PDF URLs, verifies the response is really a PDF, then
saves it under ``data/<session_id>/`` and runs the existing PDF ingestor.
"""

import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.core.config import settings
from app.core.sessions import UPLOAD_ROOT, session_manager
from app.tools.ingestor import ingest_pdf

_OPENALEX_API = "https://api.openalex.org/works"
_USER_AGENT = f"PaperAgent/1.0 (mailto:{settings.CROSSREF_MAILTO})"
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"'<>()\[\]*]+", re.IGNORECASE)
_PDF_MAX_BYTES = 80 * 1024 * 1024


def _session_id(config: RunnableConfig) -> str:
    """Pull the session id (== LangGraph thread_id) out of the run config."""
    return ((config or {}).get("configurable") or {}).get("thread_id", "")


def _normalize_query(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^doi:\s*", "", s, flags=re.IGNORECASE)
    return s.strip().rstrip(".,;:)]*")


def _is_pdf_url(url: str) -> bool:
    path = urlparse(url or "").path.lower()
    return path.endswith(".pdf")


def _safe_filename(seed: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", (seed or "paper")).strip("._-")
    stem = stem[:90] or "paper"
    return stem if stem.lower().endswith(".pdf") else f"{stem}.pdf"


def _looks_like_pdf(content: bytes, content_type: str) -> bool:
    if content[:5] == b"%PDF-":
        return True
    return "application/pdf" in (content_type or "").lower() and bool(content)


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _pdf_candidates_from_work(work: Dict[str, Any]) -> List[str]:
    candidates: List[str] = []

    oa = work.get("open_access") or {}
    if oa.get("oa_url"):
        candidates.append(oa["oa_url"])

    for key in ("best_oa_location", "primary_location"):
        loc = work.get(key) or {}
        if loc.get("pdf_url"):
            candidates.append(loc["pdf_url"])
        landing = loc.get("landing_page_url") or ""
        if _is_pdf_url(landing):
            candidates.append(landing)

    for loc in work.get("locations") or []:
        if loc.get("pdf_url"):
            candidates.append(loc["pdf_url"])
        landing = loc.get("landing_page_url") or ""
        if _is_pdf_url(landing):
            candidates.append(landing)

    return _dedupe([u for u in candidates if str(u).startswith(("http://", "https://"))])


def _work_label(work: Dict[str, Any], fallback: str) -> str:
    title = (work.get("title") or "").strip()
    doi = (work.get("doi") or "").replace("https://doi.org/", "")
    return title or doi or fallback


def _openalex_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    params = {
        "search": query,
        "per-page": max(1, min(max_results, 10)),
    }
    if settings.OPENALEX_API_KEY:
        params["api_key"] = settings.OPENALEX_API_KEY
    resp = httpx.get(
        _OPENALEX_API,
        params=params,
        timeout=20.0,
        headers={"User-Agent": _USER_AGENT},
    )
    resp.raise_for_status()
    return list((resp.json().get("results") or []))


def _download_pdf(url: str) -> Optional[bytes]:
    headers = {
        "Accept": "application/pdf,*/*;q=0.8",
        "User-Agent": _USER_AGENT,
    }
    with httpx.stream(
        "GET", url, headers=headers, timeout=45.0, follow_redirects=True
    ) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        chunks: List[bytes] = []
        total = 0
        for chunk in resp.iter_bytes():
            if not chunk:
                continue
            chunks.append(chunk)
            total += len(chunk)
            if total > _PDF_MAX_BYTES:
                raise ValueError("PDF is larger than the 80 MB safety limit.")
        content = b"".join(chunks)
    return content if _looks_like_pdf(content, content_type) else None


def _save_pdf(session_id: str, filename_seed: str, content: bytes) -> str:
    upload_dir = os.path.join(UPLOAD_ROOT, session_id)
    os.makedirs(upload_dir, exist_ok=True)
    filename = _safe_filename(filename_seed)
    path = os.path.join(upload_dir, filename)
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(path):
        path = f"{base}_{i}{ext}"
        i += 1
    with open(path, "wb") as fh:
        fh.write(content)
    return path


@tool
def find_and_ingest_open_access_pdf(query_or_doi: str, config: RunnableConfig) -> str:
    """
    Search for an open-access academic PDF, download it, ingest it, and attach it
    to the current chat session.

    Use this when the user asks to find an open-access PDF on the web and add it
    to the conversation. Pass a DOI when available for best precision; otherwise
    pass the paper title or a focused search query.

    Args:
        query_or_doi: DOI, paper title, or focused paper search query.
    """
    session_id = _session_id(config)
    if not session_id:
        return "Error: no active session; cannot attach an open-access PDF."

    query = _normalize_query(query_or_doi)
    if not query:
        return "Error: provide a DOI, paper title, or search query."

    direct_candidates = [query] if _is_pdf_url(query) else []

    if direct_candidates:
        works = []
    else:
        try:
            works = _openalex_search(query)
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code in (401, 403, 409, 429):
                return (
                    "OpenAlex declined the search request. Configure OPENALEX_API_KEY "
                    "or try again later."
                )
            return f"Error searching OpenAlex (HTTP {code})."
        except Exception as e:
            return f"Error searching for open-access PDFs: {str(e)}"

    attempts: List[str] = []
    candidates: List[tuple[str, str]] = [(u, query) for u in direct_candidates]
    for work in works:
        label = _work_label(work, query)
        for url in _pdf_candidates_from_work(work):
            candidates.append((url, label))

    candidates = [(u, label) for u, label in candidates if u]
    if not candidates:
        return (
            "No open-access PDF URL found. I found metadata, but no downloadable "
            "PDF link was exposed by the open index."
        )

    for url, label in candidates:
        try:
            content = _download_pdf(url)
            attempts.append(url)
            if not content:
                continue
            file_path = _save_pdf(session_id, label, content)
            msg = ingest_pdf.invoke({"file_path": file_path})
            if isinstance(msg, str) and msg.startswith("Error"):
                return f"Downloaded PDF to {file_path}, but ingestion failed: {msg}"
            session_manager.sync_add_files(session_id, [file_path])
            return (
                f"Downloaded and ingested open-access PDF: {file_path}\n"
                f"Source: {url}\n"
                f"{msg}"
            )
        except Exception:
            attempts.append(url)
            continue

    tried = "\n".join(f"- {u}" for u in _dedupe(attempts[:8]))
    return (
        "Found candidate open-access links, but none returned a usable PDF. "
        f"Tried:\n{tried}"
    )
