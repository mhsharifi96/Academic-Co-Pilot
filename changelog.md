# Changelog

All notable changes to this project. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/). Dates are YYYY-MM-DD.

## [Unreleased]
Work in progress on the current branch (`main`) — not yet committed. Adds the
authentication and persistence layer on top of the original agent MVP:
### Added
- **Dynamic wizards — admin-authored guided workflows (en/fa).** Admins define a
  `Wizard` (unique slug, internal `name`, and per-language `title_*` /
  `short_description_*`) with an ordered list of `WizardStep`s; each step carries
  a `guideline_prompt` that steers the agent and a `max_messages` cap. A user
  picks one from a **public** landing page (`#/`, no token required), signs in,
  and runs it as a guided chat: the current step's prompt is injected every turn
  through the per-turn context channel, and using up the step's cap advances the
  run automatically — exhausting the last step's cap completes it. The transcript
  is persisted as real rows (`wizard_messages`), not just checkpointer state, so
  a run can be left and continued.
  - New models (`app/models/wizard.py`): `Wizard`, `WizardStep`, `WizardRun`,
    `WizardMessage`; DDL parity file `migrations/20260811_add_wizard.sql`.
  - The step state machine and localisation helpers are pure functions in
    `app/services/wizard_service.py` (`apply_turn`, `next_step_id`,
    `reordered_positions`, `resolve_locale`, `localized`, `slugify`,
    `build_step_guidance`), unit-tested offline in `tests/test_wizard.py`.
    `apply_turn` compares with `>=` so a cap an admin lowers mid-step still
    terminates, and treats a `NULL`/`0`/negative cap as *unlimited*.
  - API (`app/api/v1/endpoints/wizard.py`): public `GET /wizards`,
    `GET /wizards/{slug}`; authenticated `POST /wizard-runs` (start **or**
    resume, returning the transcript in one call), `GET /wizard-runs`,
    `GET /wizard-runs/{id}`, `POST /wizard-runs/{id}/messages`,
    `POST /wizard-runs/{id}/resume`, `DELETE /wizard-runs/{id}`; admin CRUD under
    `/admin/wizards` and `/admin/wizard-steps` including a reorder route.
    Language is chosen per request with `?lang=en|fa`; public routes return text
    already resolved for that language and never expose `guideline_prompt`.
    Admin write schemas also accept the original field spellings
    (`gaurdline_prompt`, `max_masseage`) as aliases.
  - **Three ways a step ends.** Its `max_messages` cap running out (automatic),
    the user pressing **Finish step** (`POST /wizard-runs/{id}/advance` — no
    agent call, so it costs nothing), or the user accepting the agent's
    suggestion. The agent signals "this step's goal is met" by appending a
    `[[STEP_COMPLETE]]` marker, which is stripped before the reply is persisted
    or shown and returned as `step_complete_suggested`; it never auto-advances,
    because moving on is the user's decision. A text marker rather than a tool,
    since the wizard runs on the shared agent and a wizard-only tool would have
    to be hidden from every other caller of `default_tools`. This also makes an
    **uncapped step usable** — previously it parked the run forever.
  - Runs execute on the existing shared `AcademicAgent` — no third graph. Each
    run is backed by a real `ChatSession` (`agent_type="wizard"`) whose id is the
    LangGraph `thread_id`, so uploads and the history/plan endpoints work
    unchanged. Three guards keep the counter honest: `POST /chat` and
    `DELETE /sessions/{id}` return 409 for a wizard thread, and wizard sessions
    are excluded from the chat sidebar.
  - `screen_message` gained `scope_check: bool = True`
    (`app/agents/guardrails.py`). A wizard can opt out of the *academic scope*
    classifier via `Wizard.enforce_scope_guardrail` while the deterministic
    jailbreak rules always run. A blocked turn persists nothing and does not
    burn a step allowance.
  - `chat.py`'s `_build_context_message` / `_final_text` moved to
    `app/agents/context.py` (`build_session_context`, `final_text`) and are now
    shared by both endpoints.
  - Frontend: a public bilingual landing page plus the run/continue UI —
    `WizardLanding`, `WizardCard`, `WizardDetail`, `WizardRunner`,
    `WizardStepper` (sticky under the topbar, with the Finish control),
    `WizardRunsPage`, `WizardAdminPanel` (a tab inside the existing Admin
    page), `WizardEditor`, `LangToggle`, `WizardIcon`. Two new dependency-free modules back them:
    `frontend/src/i18n.js` (en/fa dictionary, `LangProvider`, `useT`, keeps
    `<html lang|dir>` in sync) and `frontend/src/router.js` (a small hash router
    — `#/`, `#/wizards/:slug`, `#/runs/:id`, `#/runs`, `#/app` — mounted above
    the app's auth gate so the landing page is reachable while signed out;
    wizard administration is a tab in the Admin page, not a route). Styling adds Crimson Pro / Atkinson Hyperlegible / Vazirmatn,
    an additive token block, SVG icons instead of emoji, staggered reveals that
    respect `prefers-reduced-motion`, and an `html[dir="rtl"]` patch block for
    the older physically-positioned chat chrome.
- **Chat UI/UX pass.** Audited the chat surface in a real browser against the
  `ui-ux-pro-max` rule set and fixed what the measurements flagged:
  - **Reading column.** Messages ran edge-to-edge across the pane; the
    transcript and the composer now share a centred 56rem column, and message
    text is 15px/1.65 (was 14px/1.5) since assistant replies are prose.
  - **Scroll position is no longer stolen.** The window auto-scrolled on every
    update, so a reply landing while you read back yanked you to the bottom.
    It now follows only when you are already there, and offers a *Jump to
    latest* pill when you are not.
  - **Screen readers announce replies.** The transcript is a
    `role="log"` / `aria-live="polite"` region; previously a new answer was
    silent. The composer, the file input and the open-by-key field gained
    accessible names, and the rename/delete buttons gained labels naming the
    chat they act on.
  - **Hit areas.** The rename/delete controls were 21×21px — kept visually
    small but given a 44×44 target; Send 55×34 → 86×40, session title 22 → 34,
    nav links 32 → 36.
  - **Typing indicator.** The static "Co-Pilot is thinking…" line is now an
    animated three-dot bubble shaped like the reply that is coming.
  - **Icons.** `WizardIcon` is generalised to `Icon` and the chat's `✎`/`✕`/`+`
    glyphs are SVG, matching the wizard surface; emoji can't take a colour
    token and mean nothing to a screen reader.
  - A shared focus-visible ring across chat, composer and sidebar controls.
  - **Scrollbar moved back to the window edge.** The wizard transcript was both
    the scroll container *and* the centred 56rem column, so its scrollbar sat at
    the column's edge — floating mid-page, and on the inner edge in RTL. Split
    into a full-width `.wz-thread` scroller with a `.wz-thread-inner` column,
    matching the fix already applied to the chat.
  - **Suggested follow-up questions.** A *Suggest questions* control above the
    wizard composer asks a cheap model for three questions the user could send
    next, given the step's goal and the tail of the conversation. Each is an
    accordion: one line collapsed, expanding to the full question plus why it
    helps, with a separate send icon so a stray click can never post something
    unread. Written in the user's voice and in the active language, so the
    chosen one is sent verbatim.
    - **On demand, never automatic** (`POST /wizard-runs/{id}/suggestions`) —
      it is a second LLM call and it is billed, so it only runs when asked.
    - A plain model call, not an agent turn: no tools needed, and it must not
      touch the LangGraph thread or land in the transcript.
    - Prompt building and reply parsing are pure functions
      (`build_suggestions_prompt`, `parse_suggestions`) tested offline; the
      parser tolerates code fences and prose, drops duplicates and malformed
      entries, and caps the count. The endpoint fails soft — a model error
      returns no suggestions rather than blocking a user mid-conversation.
  - **The Finish control names its destination** ("Next: screen results"), so
    ending a step is a decision rather than a leap. Hidden below 640px where the
    header is already tight.
- **`feature.md` — complete feature catalogue.** A single document listing every
  user-facing capability grouped by area (the two agents and session binding,
  guardrails and HITL, literature discovery across Scopus/arXiv/Crossref/OpenAlex,
  ingestion and RAG, the provider PDF download queue, screening, the drafting and
  export pipeline, quality tooling, analytics and infographics, auth/billing/admin,
  the frontend, the full API surface, platform features, and known limitations).
  Linked from the companion-docs list in `CLAUDE.md`.
- **Provider PDF download queue (DOI → PDF → ingest → attach).** Users can now
  pull a paper's full text from the external provider. The frontend detects DOIs
  in assistant messages and shows a `📄 Get PDF` chip → a confirmation modal
  (`DownloadModal.jsx`) that queues a job (`POST /downloads`). A single DB-backed
  queue (`download_jobs` table, `app/models/downloads.py`) is drained by one
  background worker (`app/core/download_worker.py`, started in the lifespan,
  guarded by `ENABLE_DOWNLOAD_WORKER`) that runs jobs one-at-a-time. On success
  the PDF is ingested (`ingest_pdf`) and registered on the session, so it becomes
  context for future messages; on `404` it retries up to 3× by rescheduling a
  future `available_at` (10 then 20 min) — the worker never sleeps, so other jobs
  keep flowing. Business logic (quota, scheduling, fairness, retry) lives in pure,
  unit-tested functions in `app/services/download_service.py`
  (`tests/test_downloads.py`). Per-user quota (10 / rolling 24h; retries and
  duplicate active DOIs don't consume quota), a FAST (requests 1–3, ~1h target)
  vs STANDARD (4–10, spread over 24h with per-user jitter) priority split, and a
  fair scheduler that rotates users within a priority round, applies FAST→STANDARD
  anti-starvation, and lets near-deadline FAST jobs jump the queue. On terminal
  failure the chat offers "Upload PDF" (reusing the existing upload/ingest path)
  or "Continue without PDF" (`DownloadStatus.jsx`). The provider token is
  backend-only (`PROVIDER_TOKEN`) and never sent to the browser.
- **Per-user balance + usage billing.** Each account now has a `balance` (USD,
  default `$0.50`, configurable via `DEFAULT_USER_BALANCE`). Every chat/resume
  turn measures its token usage (`BaseAgent.run`/`resume` now wrap the graph
  invoke in `get_usage_metadata_callback` and return `(result, usage)`), converts
  it to a dollar cost (`COST_INPUT_PER_1M` / `COST_OUTPUT_PER_1M`), deducts it
  from the user (`app/services/billing_service.py`), and writes an audit row to
  the new `usage_records` table. A user at/below `MIN_BALANCE_TO_CHAT` is blocked
  with HTTP 402. The billed balance is returned on `ChatResponse.balance` and
  shown live in the top bar. Toggle the whole thing with `ENABLE_BILLING`.
- **Admin console for managing balances.** New `is_admin` flag on `User`
  (the first account to register becomes admin). New admin-only endpoints
  (`app/api/v1/endpoints/admin.py`): `GET /admin/users`, `PATCH /admin/users/{id}`
  (set balance / toggle admin), `POST /admin/users/{id}/adjust-balance`. Gated by
  the new `get_current_admin` dependency. New `AdminPage.jsx` (linked from the top
  bar for admins) lists users and edits balances inline / with quick-credit buttons.
- **Agent guardrails.** Every incoming message is screened before the agent runs
  (`app/agents/guardrails.py`): fast keyword/regex rules catch obvious
  prompt-injection/jailbreak phrasings, then a cheap LLM classifier decides
  whether the request is in-scope (academic research) and free of
  jailbreak/system-abuse intent. Blocked messages return `status="blocked"` with a
  polite refusal and are never billed; the screen *fails open* on classifier
  errors. Both agents' system prompts also gained a non-negotiable "Scope &
  safety" section. Toggle with `ENABLE_GUARDRAILS`.
### Fixed
- **`analytics_sandbox` now self-heals on error instead of giving up.** Errors from
  the Python REPL were returned as `repr(e)` strings mislabeled `"Execution Result:"`,
  so failures (commonly `NameError: df is not defined`, since the sandbox doesn't
  retain variables between calls) looked like successful output and the agent would
  ask the user to intervene. The tool now detects the error form and, on failure,
  asks the LLM to rewrite the code as a self-contained script and reruns it — up to
  2 retries — before reporting back. The tool docstring + `skills.md` now tell the
  agent each call is a fresh environment, so scripts should re-read their CSVs.
- **Uploaded files now reappear when reloading a saved session.** The file list
  was tracked only in `SessionManager`'s in-memory store, so after a server
  restart (or any time a session wasn't already in memory) the sidebar,
  `@`-mention picker, and the agent's per-turn context all showed no files even
  though the uploads still existed on disk under `data/<session_id>/`.
  `SessionManager.get_files` now rehydrates the list from that directory, so all
  three callers survive restarts.
### Added
- **Provider-agnostic LLM repository + 4 new tools (on both agents).** New
  `app/repositories/llm.py` (`LLMRepository` / `llm_repo`) is the single seam for
  chat + image model calls, with two tiers — `default` (`OPENAI_MODEL`) and
  `powerful` (`POWERFUL_MODEL`, default `gpt-5.5`) — plus `generate_image()` (OpenAI
  `IMAGE_MODEL`, default `gpt-image-1`). Swap providers by editing this one file.
  New config: `POWERFUL_MODEL`, `IMAGE_MODEL`. Four new `@tool`s registered via
  `app/agents/tools.py:default_tools` (so academic **and** deep agents get them):
  - `validate_references` — resolves every DOI/URL and uses the powerful model to
    flag broken links and hallucinated / mis-attributed citations.
  - `humanize_text` — powerful-model rewrite for natural, human-sounding prose
    (reduces AI-detection signal) while preserving facts and citations.
  - `generate_infographic` — designs a prompt then renders an infographic PNG to
    `output_figures/`; **added to `INTERRUPT_TOOLS`** (writes a file).
  - `suggest_venues` — recommends journals/conferences/publishers by aggregating
    where similar papers were published (via OpenAlex).
  Pure helpers are unit-tested offline (`tests/test_reference_checker.py`,
  `tests/test_venue_suggester.py`, `tests/test_llm_repo.py`); documented in
  `skills.md` and `.env.example`.
- **OpenAlex literature search (`search_openalex`).** A new tool in
  `app/tools/literature.py` that searches OpenAlex (~250M scholarly works) and
  returns title, authors, year, venue, citation count, open-access status/link,
  DOI, OpenAlex id, and an abstract snippet (reconstructed from OpenAlex's
  `abstract_inverted_index`). Registered on **both** agents via
  `app/agents/tools.py:default_tools` and trims payloads with the API `select`
  param. OpenAlex requires an API key for non-trivial use as of 2026-02-13 (the
  old `mailto` polite pool was retired), so the tool sends the optional
  `OPENALEX_API_KEY` when set, runs keyless for light/testing use, and returns a
  friendly message on 401/403/409/429 (allowance exhausted / rate-limited). Pure
  parse helpers (`_parse_openalex_results`, `_reconstruct_abstract`) are
  unit-tested offline in `tests/test_literature.py`. Documented in `skills.md`,
  `.env.example`, and both agents' system prompts.
- **License: PolyForm Noncommercial 1.0.0.** Added a `LICENSE` file (© 2026
  mhsharifi96) making the project source-available for noncommercial use only —
  personal, research, education, and non-profit use is permitted; commercial use
  is not. Declared via `license`/`license-files` in `pyproject.toml`, a `license`
  field in `frontend/package.json`, and a License section in the README.
- **Second selectable agent: a "Deep Agent" (`deepagents`).** Alongside the
  existing `AcademicAgent`, the app now builds a `DeepResearchAgent`
  (`app/agents/deep_agent.py`) on top of LangChain's `deepagents.create_deep_agent`.
  It runs fully autonomously — built-in `write_todos` planning, a thread-scoped
  virtual-filesystem working memory, and **no** human-in-the-loop — while sharing
  the academic agent's tools (minus the bespoke `write_plan`/`update_plan`, now
  factored into `app/agents/tools.py:default_tools`) and the same Postgres
  checkpointer. The user picks the agent **before** the first message via a new
  `AgentSelector` card in the chat window; the choice is stored on the
  `ChatSession.agent_type` column and bound to the session for "load & continue".
  The Plan sidebar reflects the deep agent's `todos` for deep sessions. New
  `agent_type` field on `ChatRequest`, `SessionSummary`, and the history response.
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
- **`networkx` and `wordcloud` in the analytics sandbox**: added as project
  dependencies and pre-imported into the `analytics_sandbox` namespace as `nx`
  (graphs/networks) and `WordCloud` (word-cloud images), alongside `pd`/`np`/`plt`,
  so the agent can generate network graphs and word clouds without an import step.
  Run `uv sync` to install. Tool docstring + `skills.md` updated.
### Changed
- `app/main.py` now runs `init_models()` and mounts the auth router on startup.
- Chat/files/ingestion/sessions endpoints now require auth.
- Frontend `App.jsx`, `api.js`, `Message.jsx`, `SessionBar.jsx`, styles updated
  for the auth flow; `frontend/src/sessions.js` removed.
- `docker-compose.yml` / `.env.example` add `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- **The agent now runs its whole plan autonomously by default.** New
  `REQUIRE_TOOL_APPROVAL` setting (default `false`) controls human-in-the-loop:
  when off, the gated tools (`analytics_sandbox`, `screen_abstracts_csv`,
  `ingest_pdf`, `draft_paper_section`, `compile_paper`) run without pausing, so the
  agent executes the full task end-to-end and returns the final result instead of
  asking for approval on each step. `build_hitl_middleware()` returns `None` when
  off (the agent omits the middleware), and the system prompt adapts to describe
  autonomous vs. approval-gated drafting. Set `REQUIRE_TOOL_APPROVAL=true` in `.env`
  to restore the approve/edit/reject flow.

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
