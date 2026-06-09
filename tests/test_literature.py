"""
Unit tests for the pure parsing/formatting helpers behind the literature tools
(app/tools/literature). No network — we feed canned arXiv Atom XML and Crossref
JSON straight to the parsers.

Fixture-free so the suite also runs under tests/run_all.py.
"""

from app.tools.literature import _parse_arxiv_atom, _format_crossref_work, _bibtex_key


_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.01234v1</id>
    <published>2024-01-02T00:00:00Z</published>
    <title>Agentic RAG for
      Legal Compliance</title>
    <summary>We present an agentic retrieval-augmented system.</summary>
    <author><name>Ada Lovelace</name></author>
    <author><name>Alan Turing</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2312.09999v2</id>
    <published>2023-12-15T00:00:00Z</published>
    <title>Second Paper</title>
    <summary>Another abstract.</summary>
    <author><name>Grace Hopper</name></author>
  </entry>
</feed>"""


def test_parse_arxiv_extracts_all_entries():
    papers = _parse_arxiv_atom(_ARXIV_XML)
    assert len(papers) == 2


def test_parse_arxiv_fields_and_whitespace_normalised():
    p = _parse_arxiv_atom(_ARXIV_XML)[0]
    assert p["title"] == "Agentic RAG for Legal Compliance"  # newline/indent collapsed
    assert p["authors"] == "Ada Lovelace, Alan Turing"
    assert p["year"] == "2024"
    assert p["id"] == "2401.01234v1"  # stripped of the /abs/ prefix
    assert p["link"] == "http://arxiv.org/abs/2401.01234v1"


def test_parse_arxiv_empty_feed():
    empty = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
    assert _parse_arxiv_atom(empty) == []


_CROSSREF_WORK = {
    "title": ["Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"],
    "author": [
        {"given": "Patrick", "family": "Lewis"},
        {"given": "Ethan", "family": "Perez"},
    ],
    "issued": {"date-parts": [[2020, 5, 22]]},
    "container-title": ["NeurIPS"],
    "DOI": "10.5555/3495724.3496517",
    "type": "journal-article",
}


def test_bibtex_key_uses_first_author_lastname_and_year():
    assert _bibtex_key(["Patrick Lewis", "Ethan Perez"], "2020") == "lewis2020"
    assert _bibtex_key([], "") == "anonn.d."


def test_format_crossref_metadata_and_bibtex():
    out = _format_crossref_work(_CROSSREF_WORK)
    assert "Retrieval-Augmented Generation" in out
    assert "Patrick Lewis, Ethan Perez" in out
    assert "2020" in out
    assert "NeurIPS" in out
    assert "10.5555/3495724.3496517" in out
    # BibTeX block
    assert "@article{lewis2020," in out
    assert "author  = {Patrick Lewis and Ethan Perez}" in out
    assert "doi     = {10.5555/3495724.3496517}" in out


def test_format_crossref_handles_missing_fields():
    out = _format_crossref_work({"title": ["Untitled-ish"], "type": "other"})
    assert "Untitled-ish" in out
    assert "(unknown)" in out          # missing authors/year/venue
    assert "@misc{anon" in out         # non-journal -> misc, no authors -> anon key
