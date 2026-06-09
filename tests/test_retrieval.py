"""
Unit tests for the retrieval tools (app/tools/retrieval).

`_bounded_text` is pure. `search_my_papers` is exercised by swapping the module's
`get_vector_store` for a fake (no OpenAI/DB). The LLM-backed `summarize_paper`
path is not unit-tested here. Fixture-free so the suite also runs under
tests/run_all.py.
"""

from app.tools import retrieval
from app.tools.retrieval import _bounded_text


class _FakeDoc:
    def __init__(self, content, metadata):
        self.page_content = content
        self.metadata = metadata


class _FakeStore:
    def __init__(self, docs):
        self._docs = docs

    def similarity_search(self, query, k=5):
        return self._docs[:k]


def _run_search(docs, **kwargs):
    """Call the tool with get_vector_store swapped for a fake store."""
    original = retrieval.get_vector_store
    retrieval.get_vector_store = lambda *a, **k: _FakeStore(docs)
    try:
        # .func unwraps the @tool decorator to the plain function.
        return retrieval.search_my_papers.func(query="anything", **kwargs)
    finally:
        retrieval.get_vector_store = original


def test_bounded_text_truncates_with_marker():
    out = _bounded_text("x" * 50, limit=10)
    assert out.startswith("x" * 10)
    assert "(truncated)" in out


def test_bounded_text_leaves_short_text_untouched():
    assert _bounded_text("hello") == "hello"
    assert _bounded_text(None) == ""


def test_search_formats_hits_with_source_and_page():
    docs = [
        _FakeDoc("First passage about RAG.", {"source": "/data/paper_a.pdf", "page": 2}),
        _FakeDoc("Second passage.", {"source": "/data/paper_b.pdf", "page": 0}),
    ]
    out = _run_search(docs)
    assert "paper_a.pdf p.3" in out          # page is 0-based -> displayed +1
    assert "paper_b.pdf p.1" in out
    assert "First passage about RAG." in out


def test_search_respects_k():
    docs = [_FakeDoc(f"p{i}", {"source": "x.pdf"}) for i in range(10)]
    out = _run_search(docs, k=3)
    # Header says "Top 3 passages"
    assert "Top 3 passages" in out


def test_search_empty_corpus_message():
    out = _run_search([])
    assert "No relevant passages found" in out
    assert "ingest_pdf" in out
