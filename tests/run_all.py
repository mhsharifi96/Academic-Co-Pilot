"""
Zero-dependency test runner.

Prefer running with pytest:  `pytest`  (or `uv run pytest`).
This fallback lets the suite run with only the stdlib + app deps installed:

    python tests/run_all.py

It imports each test module, runs every `test_*` callable, and reports
pass/fail counts.  A tiny `pytest.raises` shim is installed if pytest is
not available, so the existing tests work unchanged either way.
"""

import importlib
import sys
import os
import traceback
from contextlib import contextmanager

# Ensure project root is importable and env is set (mirrors conftest.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_API_KEY", "")

# Install a minimal pytest shim if pytest is not installed, so `pytest.raises`
# in the test modules still works under this runner.
try:
    import pytest  # noqa: F401
except ImportError:  # pragma: no cover
    import types

    @contextmanager
    def _raises(exc):
        try:
            yield
        except exc:
            return
        raise AssertionError(f"DID NOT RAISE {exc!r}")

    shim = types.ModuleType("pytest")
    shim.raises = _raises
    # Used as a decorator in some suites; here it's a no-op passthrough.
    shim.fixture = lambda *a, **k: (lambda f: f)
    sys.modules["pytest"] = shim


TEST_MODULES = [
    "test_hitl",
    "test_sessions",
    "test_drafter_data",
    "test_literature",
    "test_exporter",
    "test_retrieval",
    "test_deep_agent_tools",
]


def main() -> int:
    passed = failed = 0
    failures = []

    for mod_name in TEST_MODULES:
        module = importlib.import_module(f"tests.{mod_name}")
        tests = sorted(
            name for name in dir(module)
            if name.startswith("test_") and callable(getattr(module, name))
        )
        for name in tests:
            fn = getattr(module, name)
            try:
                fn()
                passed += 1
                print(f"  PASS  {mod_name}.{name}")
            except Exception:
                failed += 1
                failures.append((f"{mod_name}.{name}", traceback.format_exc()))
                print(f"  FAIL  {mod_name}.{name}")

    print("\n" + "=" * 60)
    print(f"  {passed} passed, {failed} failed")
    print("=" * 60)

    for name, tb in failures:
        print(f"\n--- {name} ---\n{tb}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
