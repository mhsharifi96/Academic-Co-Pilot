"""
Unit tests for the CSV/Excel data summariser used by the RAG drafter
(app/tools/drafter._summarize_data_files).

Pure pandas/filesystem — no OpenAI or DB access.  Written without pytest
fixtures so the suite can also run under the stdlib fallback runner
(tests/run_all.py).
"""

import os
import tempfile
import pandas as pd

from app.tools.drafter import _summarize_data_files


def _write_csv(df: pd.DataFrame, name: str = "data.csv") -> str:
    d = tempfile.mkdtemp()
    p = os.path.join(d, name)
    df.to_csv(p, index=False)
    return p


def _screening_csv() -> str:
    return _write_csv(pd.DataFrame({
        "title": ["A", "B", "C", "D"],
        "year": [2020, 2021, 2022, 2023],
        "decision": ["KEEP", "REJECT", "KEEP", "KEEP"],
    }), "screened.csv")


def test_summary_reports_shape_and_columns():
    out = _summarize_data_files([_screening_csv()])
    assert "4 rows × 3 cols" in out
    assert "title" in out and "year" in out and "decision" in out


def test_summary_includes_numeric_describe():
    out = _summarize_data_files([_screening_csv()])
    assert "Numeric summary" in out
    assert "mean" in out  # describe() stat label for the numeric 'year' column


def test_summary_includes_decision_value_counts():
    out = _summarize_data_files([_screening_csv()])
    assert "Value counts for 'decision'" in out
    assert "KEEP" in out and "REJECT" in out


def test_missing_file_is_reported_not_raised():
    out = _summarize_data_files(["does/not/exist.csv"])
    assert "file not found" in out.lower()


def test_non_data_extension_is_ignored():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "notes.txt")
    with open(p, "w") as f:
        f.write("hello")
    out = _summarize_data_files([p])
    assert out == ""  # .txt silently ignored


def test_reads_excel_files():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "results.xlsx")
    pd.DataFrame({
        "metric": ["precision", "recall"],
        "value": [0.91, 0.88],
    }).to_excel(p, index=False)
    out = _summarize_data_files([p])
    assert "results.xlsx" in out
    assert "2 rows × 2 cols" in out


def test_summary_is_truncated_when_huge():
    big = pd.DataFrame({f"col_{i}": range(50) for i in range(40)})
    p = _write_csv(big, "big.csv")
    out = _summarize_data_files([p])
    assert "(truncated)" in out
    assert len(out) <= 2500 + len("\n…(truncated)")


def test_empty_list_returns_empty_string():
    assert _summarize_data_files([]) == ""
