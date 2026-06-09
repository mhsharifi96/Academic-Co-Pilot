# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). Dates are YYYY-MM-DD.

## [Unreleased]
Work in progress on the current branch (`main`) — not yet committed. Adds the
authentication and persistence layer on top of the original agent MVP:
### Added
- **Agent task planner** (`write_plan` / `update_plan` in `app/tools/task_planner.py`):
  a self-authored todo list for multi-step jobs. The agent writes an ordered
  checklist and ticks steps off as it goes. The plan is stored per session in
  `SessionManager` (outside the message history, so it survives summarization and
  HITL pauses) and injected into each turn's context. Read-only scratch memory —
  NOT gated behind approval. Tools read `session_id` from the run config
  (`thread_id`) via an injected `RunnableConfig`, so the model never supplies it.
  - New `SessionManager` plan state + methods (`get_plan` / `set_plan` /
    `update_plan_step` + sync wrappers; sync loop-handling factored into `_run_sync`).
  - New `GET /sessions/{id}/plan` endpoint; frontend `PlanSidebar.jsx` renders a
    live progress checklist (refreshed after each reply).
  - Fix: the per-turn context message now includes the `session_id`, so
    `list_session_files` no longer relies on the model guessing it.
- **Five new agent tools**:
  - `search_my_papers` + `summarize_paper` (`app/tools/retrieval.py`) — semantic
    search over the ingested corpus and a structured single-PDF TL;DR.
  - `search_literature` (arXiv) + `resolve_citation` (Crossref) (`app/tools/literature.py`)
    — scoped scholarly lookups, no API key. Reverses the prior "no web search" non-goal.
  - `search_scopus` (Elsevier/Scopus) (`app/tools/literature.py`) — peer-reviewed/indexed
    literature with citation counts. Requires `ELSEVIER_API_KEY` (config + `.env.example`);
    a Crossref polite-pool contact is now also configurable via `CROSSREF_MAILTO`.
  - `compile_paper` (`app/tools/exporter.py`) — assembles approved sections into a
    `.docx`; HITL-gated (added to `INTERRUPT_TOOLS`).
  - New deps: `httpx`, `python-docx`. Tools registered in `AcademicAgent`.
- **JWT authentication**: `app/core/security.py`, `app/api/v1/endpoints/auth.py`
  (register/login), `User` + `ChatSession` ORM models (`app/models/auth.py`).
- **Per-user session ownership**: `app/services/session_service.py`; chat/session
  routes verify ownership (cross-user → 404).
- **App database layer**: `app/core/database.py` (async SQLAlchemy, psycopg v3).
- **Frontend auth**: `LoginPage.jsx`, `auth.js` (token in localStorage, 401 → logout),
  `GuidelinesPage.jsx`.
- Project docs: `CLAUDE.md`, `PRD.md`, `Design.md`, `project_structure.md`,
  `memory.md`, this changelog.
### Changed
- `app/main.py` now runs `init_models()` and mounts the auth router on startup.
- Chat/files/ingestion/sessions endpoints now require auth.
- Frontend `App.jsx`, `api.js`, `Message.jsx`, `SessionBar.jsx`, styles updated
  for the auth flow; `frontend/src/sessions.js` removed.
- `docker-compose.yml` / `.env.example` add `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`.

## [0.1.0] — 8e691de "improve ui"
### Changed
- Web UI improvements over the initial agent build.

## [0.0.1] — b41e355 "Academic-Co-Pilot :)"
### Added
- Initial Academic Co-Pilot: FastAPI + LangChain `create_agent` agentic RAG backend.
- Five tool families: Excel screener, PDF ingestor, paper planner/title suggester,
  RAG drafter (IEEE/APA/Vancouver), analytics sandbox.
- Stateful chat via LangGraph checkpointer; summarization + HITL middleware.
- PostgreSQL/pgvector vector store; LangSmith tracing; Docker Compose + React UI.

---
### How to maintain this file
Add an entry under `[Unreleased]` as you work; on release, rename it to the
version/commit and start a fresh `[Unreleased]`. Keep entries terse — one line
per change, grouped by Added / Changed / Fixed / Removed.
