# Project Structure

A map of the repository. Use this to locate code without re-scanning the tree.
**No Django** despite the parent folder name — this is FastAPI + LangChain.

```
PaperAgent/
├── app/                          # FastAPI backend (Python 3.11, uv-managed)
│   ├── main.py                   # App entrypoint: lifespan builds checkpointer + shared agent, mounts routers
│   ├── agents/
│   │   ├── base.py               # BaseAgent: wraps create_agent; run()/resume() one turn
│   │   ├── tools.py              # default_tools(): shared tool list for both agents
│   │   ├── academic_agent.py     # AcademicAgent: tools + middleware + system prompt (embeds skills.md)
│   │   ├── deep_agent.py         # DeepResearchAgent: autonomous deepagents agent (planning + memory, no HITL)
│   │   ├── hitl.py               # Human-in-the-loop middleware, interrupt extract/resume helpers
│   │   ├── context.py            # Per-turn context message + final-reply extraction (shared)
│   │   └── screener_agent.py     # (legacy/standalone screener agent)
│   ├── api/
│   │   ├── schemas/              # Pydantic request/response models
│   │   │   ├── chat.py           # ChatRequest, ChatResponse, ResumeRequest
│   │   │   ├── wizard.py         # Wizard/run/step schemas (public, user, admin shapes)
│   │   │   └── ingestion.py
│   │   └── v1/endpoints/
│   │       ├── auth.py           # /auth/register, /auth/login, current user
│   │       ├── chat.py           # /chat, /chat/resume  (the core endpoint)
│   │       ├── ingestion.py      # PDF ingestion endpoint
│   │       ├── files.py          # /upload (multi-file PDF/CSV)
│   │       ├── downloads.py       # /downloads (provider PDF download queue: create/status/list)
│   │       ├── wizard.py         # public /wizards catalogue, /wizard-runs, /admin/wizards
│   │       └── sessions.py       # list/rename/delete chat sessions + session files
│   ├── core/
│   │   ├── config.py             # pydantic-settings; validates env at import time
│   │   ├── database.py           # App tables: async SQLAlchemy (psycopg v3)
│   │   ├── db.py                 # Vector store: PGVector (sync psycopg2) + OpenAI embeddings
│   │   ├── checkpointer.py       # LangGraph AsyncPostgresSaver / InMemorySaver factory
│   │   ├── security.py           # JWT + bcrypt, get_current_user dependency
│   │   ├── download_worker.py    # Single background worker draining the PDF download queue
│   │   └── sessions.py           # In-memory SessionManager (files + pending interrupts)
│   ├── models/
│   │   ├── auth.py               # ORM: User, ChatSession, UsageRecord
│   │   ├── downloads.py          # ORM: DownloadJob (PDF download queue)
│   │   └── wizard.py             # ORM: Wizard, WizardStep, WizardRun, WizardMessage
│   ├── services/
│   │   ├── session_service.py    # ChatSession ownership CRUD
│   │   ├── wizard_service.py     # Wizard step state machine (pure fns) + DB wrappers
│   │   └── download_service.py   # Quota/scheduling/fairness/retry (pure fns) + DB wrappers
│   ├── repositories/             # provider-agnostic external-service seams
│   │   └── llm.py                # LLMRepository: chat (default/powerful tiers) + generate_image
│   └── tools/                    # LangChain @tool functions (the agent's skills)
│       ├── screener.py           # screen_abstracts_csv  -> color-coded .xlsx  [gated]
│       ├── ingestor.py           # ingest_pdf            -> chunks into pgvector [gated]
│       ├── planner.py            # suggest_paper_titles, generate_paper_outline, plan_paper_sections
│       ├── drafter.py            # draft_paper_section   -> RAG draft w/ citations [gated]
│       ├── sandbox.py            # analytics_sandbox     -> PythonREPL, saves PNGs [gated]
│       ├── file_utils.py         # get_csv_info, list_session_files
│       ├── retrieval.py          # search_my_papers, summarize_paper
│       ├── literature.py         # search_literature (arXiv), resolve_citation (Crossref), search_scopus, search_openalex
│       ├── reference_checker.py  # validate_references   -> link + faithfulness audit (powerful model)
│       ├── humanizer.py          # humanize_text         -> natural rewrite (powerful model)
│       ├── infographic.py        # generate_infographic  -> infographic PNG via image model [gated]
│       ├── venue_suggester.py    # suggest_venues        -> journals/conferences/publishers (OpenAlex)
│       └── exporter.py           # compile_paper        -> assembles sections to .docx [gated]
│
├── frontend/                     # React + Vite SPA
│   ├── src/
│   │   ├── App.jsx               # Root: hash router shell (public wizard routes above the
│   │   │                          #   auth gate) wrapping ChatApp (login/chat/guidelines)
│   │   ├── router.js             # useHashRoute/navigate: #/, #/wizards/:slug, #/runs/:id, #/app
│   │   ├── i18n.js               # en/fa dictionary, LangProvider/useT, keeps <html lang|dir>
│   │   ├── api.js                # Backend API wrapper (`anon: true` for the public catalogue)
│   │   ├── auth.js               # JWT in localStorage; dispatches auth:logout on 401
│   │   ├── util/doi.js           # extractDois(): detect DOIs in assistant messages
│   │   └── components/           # ChatWindow, FileSidebar, InterruptCard, LoginPage,
│   │                             #   MentionDropdown, Message, MessageInput, SessionBar/List, GuidelinesPage,
│   │                             #   DownloadModal, DownloadStatus (provider PDF download UI),
│   │                             #   WizardLanding/Card/Detail/Runner/Stepper/RunsPage,
│   │                             #   AdminWizardsPage, WizardEditor, LangToggle, WizardIcon
│   ├── vite.config.js            # Dev server proxies /api -> :8000
│   ├── nginx.conf                # Prod: serves bundle, proxies /api -> app:8000
│   └── Dockerfile
│
├── tests/                        # pytest (run offline via conftest dummy env)
│   ├── conftest.py               # Sets dummy env BEFORE app imports
│   ├── run_all.py                # stdlib-only fallback runner
│   ├── test_hitl.py, test_sessions.py, test_drafter_data.py
│
├── data/                         # Uploaded PDFs/CSVs (gitignored content)
├── output_figures/              # Sandbox-generated charts (.png)
├── skills.md                     # Tool catalog injected into the agent system prompt
├── master_prompt.md             # Original build brief (historical context)
├── docker-compose.yml            # db (pgvector) + app (FastAPI) + frontend (nginx)
├── Dockerfile                    # Backend image (uv-based)
├── pyproject.toml                # Deps (uv); pytest config
└── .env.example                  # Required env vars template
```

## Where to make common changes
- **New agent tool:** add `@tool` in `app/tools/`, register it in `AcademicAgent.__init__` tool list, document it in `skills.md`. If it executes code or mutates state, add its name to `INTERRUPT_TOOLS` in `app/agents/hitl.py`.
- **New API route:** add router in `app/api/v1/endpoints/`, include it in `app/main.py`, depend on `get_current_user` + `get_db`, verify session ownership for session-scoped routes.
- **New DB model:** add to `app/models/`, ensure it's imported so `Base.metadata.create_all` (in `init_models`) picks it up.
- **New env var:** add to `Settings` in `app/core/config.py` and to `.env.example`.
- **PDF download queue:** scheduling/quota/fairness/retry rules are pure functions in `app/services/download_service.py` (unit-tested in `tests/test_downloads.py`); the background loop is `app/core/download_worker.py`. Keep the provider token backend-only.
- **Wizards:** the step state machine lives in pure functions in `app/services/wizard_service.py` (unit-tested in `tests/test_wizard.py`) — change `apply_turn` there, not in the endpoint. A wizard run is backed by a `ChatSession` with `agent_type="wizard"`; that thread must only be advanced through `/wizard-runs/{id}/messages` (`POST /chat` and `DELETE /sessions/{id}` 409 on it).
- **New UI string:** add the key to both `en` and `fa` in `frontend/src/i18n.js` and read it with `useT()`. New CSS for the wizard surface must use logical properties (`margin-inline`, `text-align: start`) so it mirrors under `dir="rtl"` without an override.
- **New frontend page:** add a case to `parseRoute` in `frontend/src/router.js` and a branch in `App`'s router shell — above the auth gate if it should be public.
