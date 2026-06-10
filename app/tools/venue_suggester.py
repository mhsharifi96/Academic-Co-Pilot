"""
Venue / publisher suggester tool.

``suggest_venues`` takes a topic or abstract and recommends concrete places to
submit — journals, conferences, and their publishers — by looking at where the
most relevant existing papers were actually published, using OpenAlex (the same
open catalog behind ``search_openalex``). This grounds the suggestions in real
publication data (with citation signal) instead of guessing.

The aggregation helper ``_aggregate_venues`` is pure (no network) for offline
testing; only ``suggest_venues`` itself calls OpenAlex.
"""

from typing import Dict, List

import httpx
from langchain_core.tools import tool

from app.core.config import settings
from app.tools.literature import _OPENALEX_API

# Pull the fields needed to identify and rank venues.
_VENUE_SELECT = "id,title,cited_by_count,primary_location"
# How many works to sample for the aggregation (OpenAlex caps per-page at 200).
_SAMPLE_SIZE = 60


def _aggregate_venues(data: Dict, max_results: int = 10) -> List[Dict]:
    """
    Aggregate OpenAlex ``/works`` results into ranked venue suggestions. Pure
    (no network) so it can be tested offline.

    Ranks by number of matching papers, then by total citations.
    """
    results = data.get("results", []) or []
    venues: Dict[str, Dict] = {}
    for w in results:
        source = (w.get("primary_location") or {}).get("source") or {}
        name = (source.get("display_name") or "").strip()
        if not name:
            continue
        v = venues.setdefault(name, {
            "name": name,
            "type": (source.get("type") or "").strip(),
            "publisher": (source.get("host_organization_name") or "").strip(),
            "count": 0,
            "citations": 0,
            "samples": [],
        })
        v["count"] += 1
        v["citations"] += int(w.get("cited_by_count") or 0)
        title = (w.get("title") or "").strip()
        if title and len(v["samples"]) < 2:
            v["samples"].append(title)

    ranked = sorted(
        venues.values(), key=lambda x: (x["count"], x["citations"]), reverse=True
    )
    for v in ranked:
        v["mean_citations"] = round(v["citations"] / v["count"], 1) if v["count"] else 0.0
    return ranked[:max_results]


@tool
def suggest_venues(topic_or_abstract: str, max_results: int = 10) -> str:
    """
    Suggest journals, conferences, and publishers to submit an article to, based
    on where the most relevant existing papers were actually published (via
    OpenAlex). Returns ranked venues with their type, publisher, how many matching
    papers they have, and average citations.

    Use this to recommend submission targets for a paper on a given topic.

    Args:
        topic_or_abstract: The paper's topic, title, or abstract.
        max_results: Maximum number of venues to suggest (default 10, capped at 20).
    """
    params = {
        "search": topic_or_abstract,
        "per-page": _SAMPLE_SIZE,
        "select": _VENUE_SELECT,
    }
    if settings.OPENALEX_API_KEY:
        params["api_key"] = settings.OPENALEX_API_KEY

    try:
        resp = httpx.get(
            _OPENALEX_API, params=params, timeout=20.0,
            headers={"User-Agent": "PaperAgent/1.0"},
        )
        resp.raise_for_status()
        venues = _aggregate_venues(resp.json(), max_results=max(1, min(max_results, 20)))
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code in (401, 403, 409, 429):
            return (
                "OpenAlex declined the request (likely the keyless testing "
                "allowance is exhausted or rate-limited). Set OPENALEX_API_KEY in "
                "the server environment — a free key from "
                "https://openalex.org/settings/api-key grants $1 of usage per day."
            )
        return f"Error suggesting venues (OpenAlex HTTP {code})."
    except Exception as e:
        return f"Error suggesting venues: {type(e).__name__}: {e}"

    if not venues:
        return (
            f"No venues found for {topic_or_abstract!r}. Try a broader topic or a "
            "fuller abstract."
        )

    blocks = [
        f"Suggested venues for {topic_or_abstract!r} "
        f"(from where {sum(v['count'] for v in venues)}+ related papers were published):\n"
    ]
    for i, v in enumerate(venues, 1):
        kind = v["type"] or "venue"
        publisher = f"  —  Publisher: {v['publisher']}" if v["publisher"] else ""
        sample = f"\n   e.g. “{v['samples'][0]}”" if v["samples"] else ""
        blocks.append(
            f"{i}. {v['name']}  [{kind}]{publisher}\n"
            f"   {v['count']} matching paper(s), avg {v['mean_citations']} citations{sample}"
        )
    return "\n\n".join(blocks)
