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
   A second, independent **deep agent** (`deepagents.create_deep_agent`,
   `app/agents/deep_agent.py`) is built on `app.state.deep_agent`. Each session is
   bound to one of them by `ChatSession.agent_type` (`"academic"|"deep"`), chosen
   in the UI **before** the first message and immutable after. The deep agent is
   autonomous: built-in `write_todos` planning + virtual-fs memory, **no HITL**.
   Both share the tool set (`app/agents/tools.py:default_tools`) and checkpointer.
4. **HITL gating** — tools in `INTERRUPT_TOOLS` (`app/agents/hitl.py`:
   `analytics_sandbox`, `screen_abstracts_csv`, `ingest_pdf`, `draft_paper_section`)
   pause for approve/edit/reject via `/chat/resume`.
5. **Config validates at import** — `app/core/config.py` requires `OPENAI_API_KEY`
   + `DATABASE_URL`. Tests set dummies in `conftest.py` BEFORE imports.
6. **skills.md is in the system prompt** — keep it synced with registered tools.
   New tools register once in `app/agents/tools.py:default_tools` (both agents).
7. **Screening CSVs need `title` + `abstract` columns.**
7b. **Per-user balance + guardrails** (added on `prod`):
   - `User.balance` (USD, default `DEFAULT_USER_BALANCE=0.5`) + `User.is_admin`.
     `BaseAgent.run`/`resume` now return `(result, usage)`; the chat endpoint bills
     via `app/services/billing_service.py` and writes `usage_records`. Balance ≤
     `MIN_BALANCE_TO_CHAT` → HTTP 402. Toggle `ENABLE_BILLING`. New `users` columns
     added by `init_models` `ALTER ... IF NOT EXISTS`.
   - First account to register becomes admin. Admin API in
     `app/api/v1/endpoints/admin.py` (`get_current_admin`); UI in `AdminPage.jsx`.
   - Guardrail in `app/agents/guardrails.py` (`screen_message`): keyword rules +
     cheap LLM classifier, runs in the chat endpoint BEFORE the agent, **fails
     open**, blocks off-topic/jailbreak with `status="blocked"` (not billed).
     Toggle `ENABLE_GUARDRAILS`. Both agent prompts also have a "Scope & safety"
     section.
7c. **Provider PDF download queue** (added on `prod`):
   - Frontend detects DOIs in assistant messages → `📄 Get PDF` chip → modal →
     `POST /downloads`. **No agent/tool change** — it's pure frontend + REST.
   - DB-backed `download_jobs` table (`app/models/downloads.py`), one **background
     worker** (`app/core/download_worker.py`) started in the lifespan, **one job
     at a time**. Guarded by `ENABLE_DOWNLOAD_WORKER` (off in tests).
   - `PROVIDER_TOKEN` is **backend-only** — used solely in the worker's provider
     call, never sent to the frontend. Endpoint: `{PROVIDER_BASE_URL}/article/doi`.
   - Quota 10 / rolling 24h; **retries + duplicate active DOIs don't consume
     quota**. 404 → retry via a future `available_at` (10, 20 min) — the worker
     **never sleeps**; 3rd 404 → `FAILED/PDF_NOT_FOUND`.
   - FAST (requests 1–3, ~1h) vs STANDARD (4–10, spread over 24h + per-user
     jitter). Quota/scheduling/fairness/retry are **pure functions** in
     `app/services/download_service.py` (tested in `tests/test_downloads.py`).
7d. **Dynamic wizards** (admin-authored guided workflows, en/fa):
   - 4 tables in `app/models/wizard.py`: `Wizard` (slug + per-language
     `title_*`/`short_description_*`), `WizardStep` (`guideline_prompt`,
     `max_messages`, `position`), `WizardRun`, `WizardMessage`.
   - ⚠️ **Wizard transcripts ARE in the app tables** (`wizard_messages`) — the
     one exception to gotcha #1. The checkpointer still holds the graph state.
   - A run is backed by a `ChatSession` with **`agent_type="wizard"`** (a third
     value, see gotcha #3); `WizardRun.session_id` is that id and the
     `thread_id`. Runs execute on the **existing** `app.state.agent` — there is
     no wizard agent class. The step's prompt arrives via the per-turn
     `context_message`, so it survives summarization and can be swapped per step.
   - Guards: `POST /chat` and `DELETE /sessions/{id}` **409** on a wizard thread;
     wizard sessions are filtered out of `list_user_sessions`. Break these and
     the step counter silently stops advancing.
   - Step advance is `apply_turn` in `app/services/wizard_service.py` (pure,
     tested in `tests/test_wizard.py`): count the turn, compare `>=` the cap,
     advance or complete; `NULL`/`0`/negative cap means **unlimited**. The
     advance happens **after** the agent replies.
   - Three ways a step ends: the cap, the user's **Finish step**
     (`apply_advance` / `POST /wizard-runs/{id}/advance`, no agent call), or the
     user accepting the agent's suggestion. The agent suggests by appending
     `[[STEP_COMPLETE]]`; `extract_completion_signal` strips it before persist
     **and** display and returns `step_complete_suggested`. It never
     auto-advances. An uncapped step is only escapable via Finish step.
   - Wizard admin is a **tab inside AdminPage**, not a route
     (`WizardAdminPanel.jsx`). The stepper is `position: sticky`.
   - `screen_message(msg, scope_check=False)` skips only the academic-scope
     classifier (jailbreak rules always run) — driven by
     `Wizard.enforce_scope_guardrail`.
   - Locale is `?lang=en|fa`; public routes resolve one language and never expose
     `guideline_prompt`. Admin write schemas also accept the original spellings
     `gaurdline_prompt` / `max_masseage` as aliases.
   - Frontend: hash router (`frontend/src/router.js`) mounted **above** the auth
     gate so `#/` is public; `frontend/src/i18n.js` holds the en/fa dictionary
     and drives `<html lang|dir>`. New CSS uses logical properties for RTL.
   - On success the PDF goes through the **same ingestion path** as `/upload`
     (`ingest_pdf` + `session_manager.add_files`) → becomes conversation context.
8. **LLM/image calls have a central seam** — `app/repositories/llm.py`
   (`llm_repo`): tiers `default` (`OPENAI_MODEL`) vs `powerful` (`POWERFUL_MODEL`,
   e.g. gpt-5.5) + `generate_image` (`IMAGE_MODEL`). New code should call it;
   the older agents/tools still build `ChatOpenAI` directly. Swap providers here.

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
