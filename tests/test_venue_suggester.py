"""
Offline unit tests for the pure venue-aggregation helper
(app/tools/venue_suggester). No network.
"""

from app.tools.venue_suggester import _aggregate_venues


def _work(venue, vtype, publisher, citations, title):
    return {
        "title": title,
        "cited_by_count": citations,
        "primary_location": {
            "source": {
                "display_name": venue,
                "type": vtype,
                "host_organization_name": publisher,
            }
        },
    }


_DATA = {
    "results": [
        _work("Journal of AI", "journal", "Elsevier", 100, "Paper A"),
        _work("Journal of AI", "journal", "Elsevier", 50, "Paper B"),
        _work("NeurIPS", "conference", "NeurIPS Foundation", 200, "Paper C"),
        _work("", "journal", "Nobody", 5, "No-venue paper"),     # skipped (no name)
        {"title": "Locationless", "cited_by_count": 9},           # no primary_location
    ]
}


def test_aggregate_ranks_by_count_then_citations():
    venues = _aggregate_venues(_DATA, max_results=10)
    # Two named venues survive (empty-name + locationless dropped).
    assert len(venues) == 2
    # Journal of AI has 2 papers vs NeurIPS 1 -> ranked first by count.
    assert venues[0]["name"] == "Journal of AI"
    assert venues[0]["count"] == 2
    assert venues[0]["publisher"] == "Elsevier"
    assert venues[0]["mean_citations"] == 75.0      # (100+50)/2
    assert venues[1]["name"] == "NeurIPS"
    assert venues[1]["type"] == "conference"


def test_aggregate_collects_sample_titles_capped():
    venues = _aggregate_venues(_DATA)
    joai = next(v for v in venues if v["name"] == "Journal of AI")
    assert joai["samples"] == ["Paper A", "Paper B"]  # at most 2


def test_aggregate_respects_max_results():
    assert len(_aggregate_venues(_DATA, max_results=1)) == 1


def test_aggregate_empty():
    assert _aggregate_venues({}) == []
    assert _aggregate_venues({"results": []}) == []
