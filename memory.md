# Memory — Quick Facts for the Agent

Durable, high-signal facts to read FIRST. Designed to save tokens: prefer this
over re-scanning the codebase. For depth see `Design.md`, `PRD.md`,
`project_structure.md`, `CLAUDE.md`.

## Identity
- **Name:** Academic Co-Pilot ("PaperAgent"). Agentic RAG research assistant.
- **Stack:** FastAPI + LangChain 1.0 `create_agent` (LangGraph) + OpenAI + Postgres/pgvector + React/Vite.
- ⚠️ **No Django** despite the `django/PaperAgent` folder path.

## Gotchas (the things that trip people up)
1. **Three separate Postgres stores, one DB** — app tables (psycopg v3 async,
   `core/database.py`), vector store (psycopg2 sync PGVector, `core/db.py`),
   conversation checkpointer (LangGraph AsyncPostgresSaver, `core/checkpointer.py`).
   **Chat history is in the checkpointer, NOT the app tables.**
2. **Two "session" things** — `ChatSession` DB row (ownership/title) vs in-memory
   `SessionManager` (files + pending interrupt). `session_id == thread_id == ChatSession.id`.
3. **One shared agent** built in `app/main.py` `lifespan`, on `app.state.agent`.
4. **HITL gating** — tools in `INTERRUPT_TOOLS` (`app/agents/hitl.py`:
   `analytics_sandbox`, `screen_abstracts_csv`, `ingest_pdf`, `draft_paper_section`)
   pause for approve/edit/reject via `/chat/resume`.
5. **Config validates at import** — `app/core/config.py` requires `OPENAI_API_KEY`
   + `DATABASE_URL`. Tests set dummies in `conftest.py` BEFORE imports.
6. **skills.md is in the system prompt** — keep it synced with registered tools.
7. **Screening CSVs need `title` + `abstract` columns.**

## Commands (uv-managed, not pip)
- Full stack: `docker-compose up --build`  (UI :5173, API :8000, docs :8000/docs)
- Backend dev: `uv run uvicorn app.main:app --reload`
- Frontend dev: `cd frontend && npm install && npm run dev`
- Tests: `uv run pytest` · one: `uv run pytest tests/test_hitl.py::name -v` · offline fallback: `python tests/run_all.py`

## Adding things (low friction)
- **Tool:** `@tool` in `app/tools/` → add to `AcademicAgent.__init__` list →
  document in `skills.md` → if it runs code/mutates state, add to `INTERRUPT_TOOLS`.
- **Route:** router in `app/api/v1/endpoints/` → include in `app/main.py` →
  depend on `get_current_user` + `get_db` → check session ownership.
- **Env var:** add to `Settings` (`core/config.py`) + `.env.example`.

## Conventions / preferences
- Strict type hints; Pydantic models for all request/response payloads.
- Modular separation: `api` / `agents` / `tools` / `core` (per `master_prompt.md`).
- Auth required on chat/session/file routes; verify ownership (cross-user → 404).

## Open items / watch-outs
- `OPENAI_MODEL` default differs: `gpt-5.4-nano` (`config.py`) vs `gpt-5.4-mini`
  (`.env.example`). Reconcile if it matters.
- `SessionManager` is in-process → assumes a single worker for file/interrupt state.
- `analytics_sandbox` uses `PythonREPL` (not hardened); HITL approval is the guard.

---
*Update this file when a non-obvious fact changes. Keep it short — it's read every session.*
