# Features — Academic Co-Pilot (PaperAgent)

A complete catalogue of what this system does, grouped by capability area. This
is the "what can it do" document; for *why* see `PRD.md`, for *how* see
`Design.md`, for *where the code lives* see `project_structure.md`, and for the
tool input schemas injected into the agent prompt see `skills.md`.

Academic Co-Pilot is an agentic RAG assistant (FastAPI backend + React/Vite SPA)
that takes a researcher from raw PDFs and CSVs to a screened spreadsheet, an
outline, cited draft sections, charts, and a compiled `.docx` — without leaving
the chat.

---

## 1. Feature map at a glance

| Area | Features |
|---|---|
| Conversation | Two selectable agents, persistent multi-session chat, auto-summarization, per-turn file context, self-authored task plan |
| Safety | Input guardrails (rules + LLM classifier), optional human-in-the-loop approval on sensitive tools, prompt-injection resistance, path-traversal-safe file serving |
| Literature discovery | Scopus, arXiv, Crossref, OpenAlex search; DOI/title → metadata + BibTeX; open-access PDF finder |
| Document intake | Multi-file upload (PDF/CSV), PDF → chunks → pgvector ingestion, provider PDF download queue by DOI |
| Retrieval | Semantic search over the ingested corpus, structured single-PDF TL;DR |
| Screening | CSV of abstracts → criteria-based decisions → color-coded Excel |
| Writing | Title suggestions, outline generation, section planning, RAG drafting (IEEE/APA/Vancouver), full-paper protocol, `.docx` compilation |
| Quality | Reference/DOI validation + hallucinated-citation detection, text humanizer, venue suggestions |
| Analysis | CSV inspection, Python sandbox with auto-retry, chart PNGs, AI infographic generation |
| Accounts | JWT auth, per-user session ownership, USD balance metering, admin console |
| Delivery | Artifact download endpoint, Docker Compose (dev + prod), offline test suite |

---

## 2. Conversation and agents

### 2.1 Two independent agents, chosen per session
The app builds **two** agents at startup (`app/main.py` lifespan) on top of one
shared checkpointer:

- **Academic agent** (`app/agents/academic_agent.py`) — a LangChain 1.0
  `create_agent` / LangGraph state machine. Supports optional human-in-the-loop
  approval and follows a strict, section-by-section paper-drafting protocol.
- **Deep research agent** (`app/agents/deep_agent.py`) — wraps
  `deepagents.create_deep_agent`. Fully autonomous: built-in `write_todos`
  planning, a thread-scoped virtual filesystem as working memory
  (`write_file` / `read_file`), and **no approval pauses** — it carries a task
  end to end.

The user picks the agent in the UI (`AgentSelector.jsx`) **before** the first
message. The choice is stored on `ChatSession.agent_type` (`"academic" | "deep"`)
and is **immutable** afterwards; `chat`, `chat/resume`, `history` and `plan` all
dispatch on it. Both agents share the same tool registry
(`app/agents/tools.py:default_tools`) — the deep agent simply omits the bespoke
`write_plan`/`update_plan` tools because `write_todos` supersedes them.

A third, focused `ScreenerAgent` (`app/agents/screener_agent.py`) exists as a
single-tool agent for literature screening only.

### 2.2 Stateful multi-session chat
Conversation state is persisted by a LangGraph `AsyncPostgresSaver` keyed by
`thread_id == session_id == ChatSession.id`. Clients send **only the new
message** — history is reloaded server-side, so sessions survive server
restarts and browser reloads. Falls back to `InMemorySaver` when `DATABASE_URL`
is unset.

Session management features:
- Create a session implicitly on first message or upload.
- List your sessions with titles and timestamps (auto-titled from the first
  message, first 120 chars).
- Rename a session (`PATCH /sessions/{id}`).
- Reload a full transcript (`GET /sessions/{id}/history`).
- Delete a session (`DELETE /sessions/{id}`).
- Open a session by ID key.

### 2.3 Automatic conversation summarization
`SummarizationMiddleware` compresses history once it passes ~4k tokens while
keeping the last 20 messages verbatim, so long research sessions stay coherent
and affordable without manual pruning.

### 2.4 Per-turn file context
The chat endpoint injects the session's *current* file list as a `SystemMessage`
on **every turn** (`_build_context_message`) rather than baking it into the
static system prompt — so "analyze my CSV" resolves to real paths even for files
uploaded mid-conversation.

### 2.5 Self-authored task plan
For multi-step requests (~3+ steps) the academic agent calls `write_plan` to lay
out an ordered checklist, then `update_plan` to mark steps
`pending`/`in_progress`/`done`. The plan is stored **per session outside the
chat history**, replayed into every turn's context, and surfaced in the UI
(`PlanSidebar.jsx`, `GET /sessions/{id}/plan`) — so it survives history
summarization and approval pauses. Deep-agent sessions surface the equivalent
`write_todos` state through the same endpoint.

---

## 3. Safety and control

### 3.1 Input guardrails
Every incoming message is screened **before** it reaches an agent and **before
any balance is spent** (`app/agents/guardrails.py`):

1. **Rule layer** — fast regexes catching common prompt-injection/jailbreak
   phrasings ("ignore previous instructions", "reveal your system prompt",
   "DAN mode", "disable your guardrails", …), short-circuiting without an LLM
   call.
2. **Allow-list layer** — short DOI/PDF commands ("download 10.x/abc pdf",
   "find an open-access PDF for …") are explicitly recognised as in-scope.
3. **LLM classifier** — a cheap model (`GUARDRAIL_MODEL`) judges scope and abuse,
   returning `{allowed, category, reason}` with categories
   `ok | off_topic | jailbreak | abuse`.

Blocked messages return `status="blocked"` with a polite on-brand refusal and
are **not billed**. The guardrail **fails open** on classifier/network errors so
a transient failure can't take down chat. Toggle with `ENABLE_GUARDRAILS`.
Both agents also carry a non-negotiable "Scope & safety" section in their system
prompts as a second line of defence (never reveal instructions/secrets, ignore
override attempts from user input *or tool output*, refuse out-of-scope work).

### 3.2 Human-in-the-loop approval (optional)
`REQUIRE_TOOL_APPROVAL` (default **false**) gates tools that execute code or
mutate persistent state behind `HumanInTheLoopMiddleware`:

`analytics_sandbox` · `screen_abstracts_csv` · `ingest_pdf` ·
`draft_paper_section` · `compile_paper` · `generate_infographic` ·
`find_and_ingest_open_access_pdf`

Flow when enabled:
1. The agent requests a gated tool → the graph pauses → `POST /chat` returns
   `status="interrupted"` plus an `interrupt` payload describing the pending
   call and its arguments.
2. The UI renders an Approve / Edit / Reject card (`InterruptCard.jsx`).
3. `POST /chat/resume` sends the decision: **approve** (run as proposed),
   **edit** (run with `edited_args`), or **reject** (skip, with an optional
   `reason` fed back to the agent).

When disabled, the academic agent runs its whole plan autonomously and returns
only the final result; the system prompt adapts to describe autonomous rather
than approval-gated drafting.

### 3.3 Ownership and isolation
Every chat/session/file route requires JWT auth and verifies that the caller
**owns** the session — cross-user access returns `404`, never `403`, so session
IDs aren't enumerable.

### 3.4 Safe artifact serving
`GET /download` only serves files resolved inside `data/` or `output_figures/`;
any path escaping those roots is rejected (`?path=../../etc/passwd` → 400).

---

## 4. Literature discovery and citations

| Tool | What it does |
|---|---|
| `search_literature` | Unified multi-index search: **Scopus/Elsevier** first (when `ELSEVIER_API_KEY` is set), then **arXiv** for recent preprints, then **Crossref** as a DOI/metadata fallback. Up to 25 results. |
| `search_scopus` | Direct Scopus-only search including citation counts; accepts plain keywords or Scopus boolean syntax. Reports a friendly message when `ELSEVIER_API_KEY` is unset. |
| `search_openalex` | Broad open catalog (~250M works): title, authors, year, venue, citation count, open-access status/link, DOI, OpenAlex id, abstract snippet. Runs keyless for light use; `OPENALEX_API_KEY` for reliable use. |
| `resolve_citation` | DOI **or** title → clean metadata (authors, year, venue, DOI) plus a ready-to-paste **BibTeX** entry, via Crossref (free, no key). Grounds citations in real metadata instead of guesses. |
| `find_and_ingest_open_access_pdf` | Searches open metadata for an OA PDF URL, downloads only verified PDF responses, saves it under the session, ingests it into the vector store, and attaches it to the session file list. **Gated by approval when HITL is on.** |
| `suggest_venues` | Aggregates where the most relevant existing papers were published (via OpenAlex) and returns ranked journals/conferences/publishers with type, publisher, matching-paper count, and average citations. |

All searches are read-only. General-purpose web browsing remains out of scope —
these are scoped scholarly lookups.

---

## 5. Document intake and RAG

### 5.1 Multi-file upload
`POST /upload` accepts multiple PDFs and CSVs at once. Files are validated
up-front (only `.pdf`/`.csv`, rejected as a batch so nothing is partially
ingested) and stored under `data/<session_id>/`, so sessions never collide.
PDFs are ingested automatically; CSVs are saved for screening/analysis.

### 5.2 PDF ingestion into the vector store
`ingest_pdf` parses a PDF, chunks the text, generates OpenAI embeddings, and
writes them to PostgreSQL/pgvector (collection `academic_papers`).

### 5.3 Corpus retrieval
- `search_my_papers` — semantic search over everything already ingested;
  returns the top-`k` most relevant passages as evidence before drafting.
- `summarize_paper` — a structured TL;DR of a single PDF
  (**Problem / Method / Data / Key Findings / Limitations**) *without* ingesting
  it into the vector DB, with an optional focus hint.

### 5.4 Session file awareness
`list_session_files` plus the per-turn context message mean the agent always
knows which files exist. The UI adds an `@`-mention picker
(`MentionDropdown.jsx`) so users can insert exact file paths into a message.

---

## 6. Provider PDF download queue (DOI → PDF → ingest → attach)

A DB-backed queue that fetches a paper's full text from an external provider and
attaches it to the conversation. Implemented entirely as frontend + REST (no
agent/tool changes).

**Entry points:** the `Downloads` tab (paste a DOI) or a `📄 Get PDF` chip the UI
shows whenever it detects a DOI in a chat message → confirmation modal → job
queued.

**Pipeline:** `POST /downloads` validates and normalizes the DOI, deduplicates
against active jobs for the same user+DOI, and creates a `download_jobs` row. A
single background worker (`app/core/download_worker.py`, started in the lifespan,
guarded by `ENABLE_DOWNLOAD_WORKER`) drains the queue **one job at a time**. On
success the PDF is saved under the session directory, ingested through the same
path as `/upload`, and added to the session file list — becoming context for
future messages. The user keeps chatting while jobs run; the UI polls every 4s.

**Statuses:** `QUEUED` · `RUNNING` · `RETRY_SCHEDULED` · `SUCCEEDED` · `FAILED`
(failure codes `PDF_NOT_FOUND`, `PROVIDER_ERROR`).

**Quota and fairness** (pure, unit-tested functions in
`app/services/download_service.py`):
- 10 originating requests per user per rolling 24h. **Retries and deduplicated
  DOIs don't consume quota.**
- Requests 1–3 are **FAST** (available immediately, ~1h target deadline);
  requests 4–10 are **STANDARD**, spread across 24h at configured offsets with
  deterministic per-user jitter so users don't all fire at once.
- Anti-starvation: after several FAST jobs an eligible STANDARD job runs.
- Deadline urgency: FAST jobs near their deadline jump the queue.
- On `404` the job retries up to 3× by rescheduling a future `available_at`
  (10 then 20 min) — the worker **never sleeps**, so other jobs keep flowing.

**Terminal failure UX:** the chat offers **Upload PDF** (same ingestion path,
from a source the user trusts) or **Continue without PDF** (answers use only
currently-available information).

**Security:** `PROVIDER_TOKEN` is backend-only and never reaches the browser.

Full operational reference: `download.md`.

---

## 7. Literature screening

`screen_abstracts_csv` evaluates a CSV of abstracts against user-supplied
inclusion/exclusion criteria and produces a **color-coded Excel workbook** with
a decision and a justification per row. Optional `feedback` carries extra
instructions; the output path defaults under `data/`. The input CSV must have
`title` and `abstract` columns. Gated by approval when HITL is on.

---

## 8. Paper planning, drafting, and export

| Stage | Tool | Detail |
|---|---|---|
| Titles | `suggest_paper_titles` | N original, catchy titles for a topic, informed by documents retrieved from the vector DB; accepts style feedback. |
| Outline | `generate_paper_outline` | Detailed hierarchical outline (Introduction, Literature Review, Methodology, …) for a topic + chosen title. |
| Section list | `plan_paper_sections` | Parses an outline into a clean, ordered list of top-level section titles, so each is drafted exactly once. |
| Drafting | `draft_paper_section` | RAG draft of one section grounded in ingested PDFs, in **IEEE / APA / Vancouver** style. Optionally grounded in quantitative data from session CSV/XLSX files (`data_files`) for empirical sections. Gated by approval when HITL is on. |
| Export | `compile_paper` | Assembles ordered `{heading, body}` sections into a single Word `.docx` under `data/`, downloadable via `/download`. Gated by approval when HITL is on. |

**Full-paper protocol.** When asked to write a whole paper the agent: ensures an
outline exists → calls `plan_paper_sections` → drafts sections **one at a time
in order** (each building on the last, `data_files` passed for empirical
sections and omitted for narrative ones) → presents the assembled paper → offers
to compile a `.docx`. With HITL enabled this becomes approve/edit/reject per
section; the deep agent runs the same protocol autonomously.

### 8.1 Quality tooling
- **`validate_references`** — audits a paper's references on two axes:
  (1) every DOI/URL is resolved **over the network**, flagging dead or fabricated
  links; (2) a *powerful* model checks each reference looks real and that the
  in-text claims citing it are actually supported — catching hallucinated or
  mis-attributed citations. Read-only.
- **`humanize_text`** — rewrites AI-drafted prose into natural, varied human
  writing (reducing AI-detector signals) while strictly preserving meaning,
  facts, numbers, and citations. Configurable tone (default `academic`). Uses
  the *powerful* model tier.
- **`suggest_venues`** — see §4.

---

## 9. Data analysis and visualization

- **`get_csv_info`** — column names, dtypes, row/column counts, and a 5-row
  preview. The agent is instructed to always call this before writing analytics
  code so column names and types are correct.
- **`analytics_sandbox`** — a Python REPL for analysis and plotting with
  `pd`, `np`, `plt`, `nx` (networkx) and `WordCloud` pre-imported, plus `re`,
  `json`, `math`, `statistics`, `datetime`, `collections`, `itertools`,
  `random`, `Counter`, `defaultdict`. Plots are saved to `output_figures/` and
  rendered inline in chat. Each call is a **fresh environment** (scripts must
  re-read their data). **Self-healing:** on an error the sandbox inspects the
  traceback and retries with corrected code up to 2 times before reporting back.
  Gated by approval when HITL is on.
- **`generate_infographic`** — turns a brief (abstract, findings, key points)
  into an infographic PNG: a model designs the layout prompt, then an image model
  (`IMAGE_MODEL`, default `gpt-image-1`) renders it into `output_figures/`.
  On-image text is kept short deliberately. Gated by approval when HITL is on.

---

## 10. Accounts, billing, and administration

### 10.1 Authentication
JWT bearer auth with bcrypt password hashing (`app/core/security.py`).
`POST /auth/register`, `POST /auth/login`, `GET /auth/me`. Tokens default to a
7-day lifetime; the SPA stores the token in localStorage and drops to the login
screen on any `401` via an `auth:logout` event.

### 10.2 Per-user balance and usage metering
Each account carries a USD `balance` (default `$0.50`, `DEFAULT_USER_BALANCE`).
Every chat/resume turn measures its token usage, converts it to a dollar cost
(`COST_INPUT_PER_1M` / `COST_OUTPUT_PER_1M`), deducts it from the user, and
writes an audit row to `usage_records`. The remaining balance is returned on
every `ChatResponse` and shown live in the top bar. A user at or below
`MIN_BALANCE_TO_CHAT` is blocked with **HTTP 402** until topped up. Admins are
never blocked. Disable metering entirely with `ENABLE_BILLING=false`.

### 10.3 Admin console
The first account to register becomes admin (or set `ADMIN_EMAIL` to promote a
specific account deterministically at startup). Admin-only endpoints
(`app/api/v1/endpoints/admin.py`, 403 for everyone else):
- `GET /admin/users` — list users with balance, admin flag, created date.
- `PATCH /admin/users/{id}` — set a balance outright and/or toggle admin.
- `POST /admin/users/{id}/adjust-balance` — add or subtract credit.

UI: `AdminPage.jsx`.

---

## 11. Frontend (React/Vite SPA)

- **Chat** with markdown rendering, inline images for generated charts, and
  clickable download links for produced artifacts.
- **Agent selector** — choose Academic vs Deep Research before the first message.
- **Session list** — switch, rename, delete, open-by-ID, start new.
- **File sidebar** — uploaded and downloaded files per session, with an
  `@`-mention picker to insert exact paths into a message.
- **Plan sidebar** — live view of the agent's task checklist / todos.
- **Interrupt card** — Approve / Edit (editable JSON args) / Reject with reason.
- **Downloads tab + DOI chips + status cards** — queue a PDF by DOI, watch job
  status, and recover from failures (upload manually or continue without).
- **Wizard landing page** — a **public**, bilingual (en/fa, RTL-aware) catalogue of
  guided workflows at `#/`, reachable without signing in; picking one leads to a
  detail page with the step outline, then to the runner.
- **Wizard runner** — the guided chat: a stepper showing "Step 2 of 5", a progress
  bar, the current step's name, and how many messages remain before the workflow
  moves on; a completion panel when the last step is done.
- **My workflows** — in-progress and finished runs, with Continue.
- **Language toggle (EN / فا)** — switches UI strings, the language the wizard API
  resolves content for, and `<html dir>`.
- **Wizard admin** — create/publish/delete workflows and edit their steps
  (bilingual fields side by side, guideline prompt, message cap, reordering).
- **Guidelines page** — in-app usage guidance.
- **Admin page** — user/balance management for admins.
- **Balance indicator** in the top bar.
- Auth is handled in `auth.js`; `api.js` wraps every backend route. nginx (Docker)
  or Vite (dev) proxy `/api` to the backend, so **no CORS config is needed** in
  either mode.

---

## 12. API surface

| Method & path | Purpose |
|---|---|
| `POST /api/v1/auth/register` | Create an account (returns a JWT) |
| `POST /api/v1/auth/login` | Log in (returns a JWT) |
| `GET /api/v1/auth/me` | Current profile (balance, admin flag) |
| `POST /api/v1/chat` | Send a message; returns `complete`, `interrupted`, or `blocked` |
| `POST /api/v1/chat/resume` | Approve / edit / reject a paused tool call |
| `POST /api/v1/upload` | Upload PDFs/CSVs to a session (PDFs auto-ingested) |
| `GET /api/v1/sessions` | List your sessions |
| `PATCH /api/v1/sessions/{id}` | Rename a session |
| `GET /api/v1/sessions/{id}/files` | Session file list |
| `GET /api/v1/sessions/{id}/plan` | Agent task plan / todos |
| `GET /api/v1/sessions/{id}/history` | Full transcript |
| `DELETE /api/v1/sessions/{id}` | Delete a session |
| `GET /api/v1/download?path=…` | Stream a generated artifact (JWT via header or `?token=`) |
| `POST /api/v1/downloads` | Queue a PDF download by DOI |
| `GET /api/v1/downloads/{job_id}` | One job's status |
| `GET /api/v1/downloads?session_id=…` | All jobs for a session + remaining quota |
| `GET /api/v1/admin/users` | *(admin)* List users |
| `PATCH /api/v1/admin/users/{id}` | *(admin)* Set balance / admin flag |
| `POST /api/v1/admin/users/{id}/adjust-balance` | *(admin)* Add or subtract credit |
| `GET /api/v1/wizards?lang=` | **Public** — published wizards, resolved for `en`/`fa` |
| `GET /api/v1/wizards/{slug}?lang=` | **Public** — one wizard + its step outline |
| `POST /api/v1/wizard-runs` | Start a wizard, or resume your active run (returns the transcript) |
| `GET /api/v1/wizard-runs?status=` | Your runs, most recently active first |
| `GET /api/v1/wizard-runs/{id}` | One run + its persisted transcript |
| `POST /api/v1/wizard-runs/{id}/messages` | Take a turn (advances the step when the cap is used up) |
| `POST /api/v1/wizard-runs/{id}/resume` | Approve / edit / reject a paused tool call in a run |
| `DELETE /api/v1/wizard-runs/{id}` | Abandon a run (transcript kept, thread + files cleared) |
| `GET|POST /api/v1/admin/wizards` | *(admin)* List all wizards / create one |
| `GET|PATCH|DELETE /api/v1/admin/wizards/{id}` | *(admin)* Read / edit / delete (409 once runs exist) |
| `POST /api/v1/admin/wizards/{id}/steps` | *(admin)* Append a step |
| `PATCH|DELETE /api/v1/admin/wizard-steps/{id}` | *(admin)* Edit / delete a step |
| `PUT /api/v1/admin/wizards/{id}/steps/reorder` | *(admin)* Rewrite step order |

Interactive docs at `http://localhost:8000/docs`.

---

## 13. Platform features

### 13.1 Three separate Postgres-backed stores
One Postgres instance, three deliberately distinct subsystems:
1. **App tables** — users, chat-session ownership, usage records, download jobs
   (async SQLAlchemy over psycopg v3); tables created on startup.
2. **Vector store** — `PGVector` + OpenAI embeddings, collection
   `academic_papers` (sync psycopg2).
3. **Conversation checkpointer** — LangGraph `AsyncPostgresSaver`.
   **Chat messages live here, not in the app tables.**

### 13.2 Central LLM seam
`app/repositories/llm.py` (`llm_repo`) routes model calls through named tiers —
`default` (`OPENAI_MODEL`) and `powerful` (`POWERFUL_MODEL`, for reference
checking and humanizing) — plus `generate_image` (`IMAGE_MODEL`). Swapping model
or provider happens in one place.

### 13.3 Feature flags (`.env` / `app/core/config.py`)
`REQUIRE_TOOL_APPROVAL` · `ENABLE_GUARDRAILS` · `ENABLE_BILLING` ·
`ENABLE_DOWNLOAD_WORKER` · `ENVIRONMENT` (`development`/`production`) ·
`ELSEVIER_API_KEY` · `OPENALEX_API_KEY` · `ADMIN_EMAIL` · `LANGSMITH_*` tracing.
Config is validated **at import** — `OPENAI_API_KEY` and `DATABASE_URL` are
required.

### 13.4 Deployment
- `docker-compose up --build` — full stack: Postgres/pgvector, API on `:8000`,
  nginx-served UI on `:5173`.
- `docker-compose.prod.yml` + `run-prod.sh` + `Caddyfile` for a production
  deployment with TLS.
- Backend hot reload: `uv run uvicorn app.main:app --reload`.
- Frontend hot reload: `cd frontend && npm run dev`.
- Dependencies managed with **uv**.

### 13.5 Fully offline test suite
`uv run pytest` runs without network or API keys — `tests/conftest.py` sets dummy
credentials and disables tracing before any app module imports. A stdlib-only
fallback runner (`python tests/run_all.py`) exists for environments without
pytest. Coverage includes HITL, guardrails, sessions, retrieval, literature
search, open-access PDF finding, the download scheduler, the drafter's data
grounding, the exporter, the reference checker, the venue suggester, the task
planner, the LLM repository, and the deep agent's tool wiring.

---

## 14. Known limitations / non-goals

- **Single-process assumptions.** `SessionManager` (uploaded file paths +
  pending interrupt) is in-memory, and the download worker is designed for one
  instance — horizontal scaling would need these externalised.
- **OpenAI-only.** No other model providers in the current build (though
  `llm_repo` is the seam where that would change).
- **No general web browsing.** Only scoped, read-only scholarly lookups.
- **No reference-manager integrations** (Zotero/Mendeley).
- **`analytics_sandbox` uses `PythonREPL`**, which is not a hardened sandbox —
  HITL approval is the guard when it matters.
- Screening CSVs must have `title` and `abstract` columns.
