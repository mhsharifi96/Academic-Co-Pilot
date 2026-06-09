# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). Dates are YYYY-MM-DD.

## [Unreleased]
Work in progress on the current branch (`main`) — not yet committed. Adds the
authentication and persistence layer on top of the original agent MVP:
### Added
- **Five new agent tools**:
  - `search_my_papers` + `summarize_paper` (`app/tools/retrieval.py`) — semantic
    search over the ingested corpus and a structured single-PDF TL;DR.
  - `search_literature` (arXiv) + `resolve_citation` (Crossref) (`app/tools/literature.py`)
    — scoped scholarly lookups, no API key. Reverses the prior "no web search" non-goal.
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
