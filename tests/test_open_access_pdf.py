from app.tools.open_access_pdf import (
    _looks_like_pdf,
    _normalize_query,
    _pdf_candidates_from_work,
    _safe_filename,
)


def test_normalize_query_strips_doi_url_and_markdown():
    assert (
        _normalize_query("https://doi.org/10.57230/ejplt242tdmcdv**")
        == "10.57230/ejplt242tdmcdv"
    )


def test_safe_filename_adds_pdf_and_removes_unsafe_chars():
    assert _safe_filename("A title: with / unsafe * chars") == "A_title_with_unsafe_chars.pdf"


def test_looks_like_pdf_accepts_magic_bytes_or_content_type():
    assert _looks_like_pdf(b"%PDF-1.7 data", "text/plain")
    assert _looks_like_pdf(b"data", "application/pdf")
    assert not _looks_like_pdf(b"<html></html>", "text/html")


def test_pdf_candidates_from_openalex_work_are_deduped():
    work = {
        "open_access": {"oa_url": "https://example.org/a.pdf"},
        "best_oa_location": {
            "pdf_url": "https://example.org/a.pdf",
            "landing_page_url": "https://example.org/page",
        },
        "primary_location": {
            "pdf_url": "https://example.org/b.pdf",
            "landing_page_url": "https://example.org/c.pdf",
        },
        "locations": [
            {"pdf_url": "https://example.org/b.pdf"},
            {"landing_page_url": "https://example.org/d.pdf"},
        ],
    }
    assert _pdf_candidates_from_work(work) == [
        "https://example.org/a.pdf",
        "https://example.org/b.pdf",
        "https://example.org/c.pdf",
        "https://example.org/d.pdf",
    ]
