"""
Shared test fixtures and environment setup.

The app's pydantic settings (app/core/config.py) require OPENAI_API_KEY and
DATABASE_URL at import time, and LangSmith tracing reaches out to the network.
We set safe dummy values here BEFORE any app module is imported so the unit
tests run fully offline (no OpenAI calls, no DB, no tracing).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGCHAIN_API_KEY", "")
