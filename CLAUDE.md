# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Academic Co-Pilot ("PaperAgent") — an agentic RAG backend (FastAPI) plus a React/Vite SPA. A single LangChain 1.0 `create_agent` (LangGraph state machine) helps researchers screen literature, ingest PDFs, plan/draft papers with citations, and run data analysis in a sandbox. Despite the folder name (`django/PaperAgent`), there is **no Django** — this is FastAPI.

## Companion docs

Several `.md` files at the repo root cover the same system from different angles — read the one that fits the task instead of re-scanning the tree, and **keep them in sync when behavior changes**:

- `memory.md` — quick high-signal facts + gotchas; read this first.
- `PRD.md` — product requirements: what/why, features (F1–F12), user flows, non-goals.
- `Design.md` — technical design: tech stack, architecture diagram, the 9 key design decisions, known limitations.
- `project_structure.md` — repository map ("where things live") + where to make common changes.
- `changelog.md` — notable changes; add an entry under `[Unreleased]` as you work.
- `skills.md` — tool catalog injected verbatim into the agent system prompt (sync with the registered tools).
- `master_prompt.md` — original build brief (historical context).

## Commands

Dependencies are managed with **uv** (not pip/poetry).

```bash
# Full stack (db + api + nginx-served UI) — UI at :5173, API at :8000, Swagger at :8000/docs
docker-compose up --build

# Backend only, hot reload (needs Postgres reachable via DATABASE_URL)
uv run uvicorn app.main:app --reload

# Frontend dev server with hot reload (proxies /api -> :8000, configured in frontend/vite.config.js)
cd frontend && npm install && npm run dev

# Tests
uv run pytest                          # all tests
uv run pytest tests/test_hitl.py       # one file
uv run pytest tests/test_hitl.py::test_name -v   # one test
python tests/run_all.py                # stdlib-only fallback runner (no pytest needed)
```

Tests run **fully offline**: `tests/conftest.py` sets dummy `OPENAI_API_KEY`/`DATABASE_URL` and disables LangSmith tracing *before* any app module imports (settings are validated at import time, so this ordering matters).

> Run **either** the Docker `frontend` service **or** the local Vite dev server — both bind port 5173.

## Configuration

Pydantic-settings (`app/core/config.py`) reads `.env` and **fails at import** if `OPENAI_API_KEY` or `DATABASE_URL` are missing. Copy `.env.example` → `.env`. Key vars: `OPENAI_API_KEY`, `OPENAI_MODEL`, `DATABASE_URL`, `JWT_SECRET`, `LANGSMITH_*`.

## Architecture

### The single shared agent
`app/main.py`'s `lifespan` builds **one** `AcademicAgent` and stores it on `app.state.agent`; request handlers fetch it via `_get_agent`. The agent is constructed *on top of* an already-opened checkpointer so the Postgres connection pool's lifecycle is owned centrally by the lifespan, not the agent.

- `app/agents/base.py` (`BaseAgent`) wraps `create_agent` with the LLM, tools, middleware, and checkpointer. `run()` invokes one turn; `resume()` continues a paused HITL graph via `Command(resume=...)`. Callers pass **only the new message** — history is reloaded from the checkpointer by `thread_id`.
- `app/agents/academic_agent.py` (`AcademicAgent`) registers the tool set, the `SummarizationMiddleware` (compresses history past ~4k tokens, keeps last 20 messages), and the HITL middleware. Its system prompt embeds `skills.md` (loaded from CWD at construction) and encodes the strict section-by-section full-paper drafting protocol.

### Three SEPARATE Postgres-backed stores — do not conflate
All three use the same Postgres instance but are deliberately distinct subsystems with different drivers:
1. **App tables** (`app/core/database.py`) — users + chat-session ownership. Async SQLAlchemy via **psycopg v3** (`postgresql+psycopg://`, rewritten by `_async_url`). `init_models()` creates tables on startup.
2. **Vector store** (`app/core/db.py`) — `PGVector` with OpenAI embeddings, collection `academic_papers`. Sync **psycopg2**.
3. **Conversation checkpointer** (`app/core/checkpointer.py`) — LangGraph `AsyncPostgresSaver` keyed by `thread_id == session_id`. Falls back to `InMemorySaver` when `DATABASE_URL` is unset. **Chat messages live here, NOT in the app tables.**

### Two distinct "session" concepts
- `ChatSession` (DB row, `app/models/auth.py`) — ownership, title, timestamps. Its `id` *is* the `session_id` *is* the LangGraph `thread_id`. Managed via `app/services/session_service.py` (`ensure_session`, `get_owned_session`, ...).
- `SessionManager` (in-memory singleton, `app/core/sessions.py`) — tracks **uploaded file paths** and the **pending HITL interrupt** per session. Not persisted. `sync_get_files` exists so `@tool` functions (which run synchronously inside the graph) can read files without deadlocking the asyncio lock.

### Human-in-the-loop (HITL) flow
HITL is **off by default** (`REQUIRE_TOOL_APPROVAL=false` in `app/core/config.py`): the agent runs its whole plan and returns the final result without pausing. When `REQUIRE_TOOL_APPROVAL=true`, `app/agents/hitl.py` gates the tools in `INTERRUPT_TOOLS` (`analytics_sandbox`, `screen_abstracts_csv`, `ingest_pdf`, `draft_paper_section`, `compile_paper`) behind `HumanInTheLoopMiddleware` (`build_hitl_middleware()` returns `None` when off, so the agent omits the middleware; `get_system_prompt` also adapts to describe autonomous vs. approval-gated drafting). Flow when enabled:
1. Agent wants a gated tool → graph pauses with `__interrupt__`. `POST /chat` returns `status="interrupted"` + an `interrupt` payload (built by `extract_interrupt`), and the interrupt is stashed in `SessionManager`.
2. Client calls `POST /chat/resume` with `approve` / `edit` (needs `edited_args`) / `reject` (optional `reason`). `build_resume_command_value` translates this into the `{"decisions": [...]}` payload the middleware expects (one decision per pending action).

When adding a tool that executes code or mutates persistent state, add its name to `INTERRUPT_TOOLS`.

### Per-turn file context
The chat endpoint injects the session's current file list as a `SystemMessage` *each turn* (`_build_context_message` → `BaseAgent.run(context_message=...)`) rather than baking it into the static system prompt, because the file set changes between requests.

### Auth
JWT bearer (`app/core/security.py`): `get_current_user` protects endpoints; bcrypt for passwords (truncated to 72 bytes deliberately). `app/api/v1/endpoints/auth.py` exposes register/login. Every chat/session request verifies the user **owns** the session (cross-user access → 404).

### Tools (`app/tools/`)
`@tool` functions, all synchronous: `screener.py` (CSV→color-coded Excel), `ingestor.py` (PDF→chunks→pgvector), `planner.py` (titles/outline/section list), `drafter.py` (RAG draft per section, optional CSV grounding via `_summarize_data_files`, IEEE/APA/Vancouver), `sandbox.py` (`PythonREPL`, saves plots to `output_figures/`), `file_utils.py` (`get_csv_info`, `list_session_files`).

### Frontend (`frontend/src/`)
React SPA. `api.js` wraps the backend; `auth.js` stores the JWT in localStorage and dispatches `auth:logout` on any 401. Components cover chat, file sidebar, `@`-mention file picker, and the Approve/Edit/Reject interrupt card. nginx (Docker) or Vite (dev) proxy `/api` to the backend, so no CORS config is needed in either mode.

## Conventions

- New API endpoints: add a router in `app/api/v1/endpoints/`, include it in `app/main.py`, depend on `get_current_user` + `get_db`, and verify session ownership for session-scoped routes.
- Agent capabilities are documented in `skills.md`, which is loaded verbatim into the system prompt — keep it in sync when changing tools.
