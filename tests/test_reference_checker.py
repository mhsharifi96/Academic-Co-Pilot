"""
Offline unit tests for the pure reference-parsing helpers
(app/tools/reference_checker). No network, no LLM.
"""

from app.tools.reference_checker import (
    _find_references_section,
    _split_reference_entries,
    _extract_references,
    _format_link_report,
)


_PAPER = """\
Introduction. We build on prior work [1] and extend the method of [2].
The approach is novel and effective.

References
[1] A. Smith, "Deep Things", Journal of Things, 2020. https://doi.org/10.1000/abc123
[2] B. Jones. Another Paper. 2019. https://example.com/paper2
"""


def test_find_references_section_after_heading():
    section = _find_references_section(_PAPER)
    assert "[1] A. Smith" in section
    assert "Introduction" not in section  # body dropped


def test_find_references_section_no_heading_returns_all():
    txt = "no heading here, just text"
    assert _find_references_section(txt) == txt


def test_split_reference_entries_uses_enumerators():
    block = _find_references_section(_PAPER)
    entries = _split_reference_entries(block)
    assert len(entries) == 2
    assert entries[0].startswith('A. Smith')  # enumerator stripped


def test_extract_references_pulls_doi_and_url():
    refs = _extract_references(_PAPER)
    assert len(refs) == 2
    assert refs[0]["doi"] == "10.1000/abc123"
    assert refs[1]["doi"] == ""                       # no DOI on ref 2
    assert refs[1]["url"] == "https://example.com/paper2"
    assert refs[0]["index"] == "1"


def test_extract_references_with_explicit_block():
    refs = _extract_references("body only", references="[1] Solo ref doi:10.5555/xy")
    assert len(refs) == 1
    assert refs[0]["doi"] == "10.5555/xy"


def test_format_link_report_marks_status():
    checked = [
        {"index": "1", "doi": "10.1/a", "url": "", "ok": "yes", "status": "resolves"},
        {"index": "2", "doi": "", "url": "http://x/y", "ok": "no", "status": "broken/404"},
        {"index": "3", "doi": "", "url": "", "ok": "", "status": "no-link"},
    ]
    report = _format_link_report(checked)
    assert "✓ resolves" in report
    assert "✗ broken" in report
    assert "no link to check" in report
