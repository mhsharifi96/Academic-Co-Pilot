# Project Structure

A map of the repository. Use this to locate code without re-scanning the tree.
**No Django** despite the parent folder name — this is FastAPI + LangChain.

```
PaperAgent/
├── app/                          # FastAPI backend (Python 3.11, uv-managed)
│   ├── main.py                   # App entrypoint: lifespan builds checkpointer + shared agent, mounts routers
│   ├── agents/
│   │   ├── base.py               # BaseAgent: wraps create_agent; run()/resume() one turn
│   │   ├── academic_agent.py     # AcademicAgent: tools + middleware + system prompt (embeds skills.md)
│   │   ├── hitl.py               # Human-in-the-loop middleware, interrupt extract/resume helpers
│   │   └── screener_agent.py     # (legacy/standalone screener agent)
│   ├── api/
│   │   ├── schemas/              # Pydantic request/response models
│   │   │   ├── chat.py           # ChatRequest, ChatResponse, ResumeRequest
│   │   │   └── ingestion.py
│   │   └── v1/endpoints/
│   │       ├── auth.py           # /auth/register, /auth/login, current user
│   │       ├── chat.py           # /chat, /chat/resume  (the core endpoint)
│   │       ├── ingestion.py      # PDF ingestion endpoint
│   │       ├── files.py          # /upload (multi-file PDF/CSV)
│   │       └── sessions.py       # list/rename/delete chat sessions + session files
│   ├── core/
│   │   ├── config.py             # pydantic-settings; validates env at import time
│   │   ├── database.py           # App tables: async SQLAlchemy (psycopg v3)
│   │   ├── db.py                 # Vector store: PGVector (sync psycopg2) + OpenAI embeddings
│   │   ├── checkpointer.py       # LangGraph AsyncPostgresSaver / InMemorySaver factory
│   │   ├── security.py           # JWT + bcrypt, get_current_user dependency
│   │   └── sessions.py           # In-memory SessionManager (files + pending interrupts)
│   ├── models/
│   │   └── auth.py               # ORM: User, ChatSession
│   ├── services/
│   │   └── session_service.py    # ChatSession ownership CRUD
│   └── tools/                    # LangChain @tool functions (the agent's skills)
│       ├── screener.py           # screen_abstracts_csv  -> color-coded .xlsx  [gated]
│       ├── ingestor.py           # ingest_pdf            -> chunks into pgvector [gated]
│       ├── planner.py            # suggest_paper_titles, generate_paper_outline, plan_paper_sections
│       ├── drafter.py            # draft_paper_section   -> RAG draft w/ citations [gated]
│       ├── sandbox.py            # analytics_sandbox     -> PythonREPL, saves PNGs [gated]
│       └── file_utils.py         # get_csv_info, list_session_files
│
├── frontend/                     # React + Vite SPA
│   ├── src/
│   │   ├── App.jsx               # Root: auth gate, routing between login/chat/guidelines
│   │   ├── api.js                # Backend API wrapper
│   │   ├── auth.js               # JWT in localStorage; dispatches auth:logout on 401
│   │   └── components/           # ChatWindow, FileSidebar, InterruptCard, LoginPage,
│   │                             #   MentionDropdown, Message, MessageInput, SessionBar/List, GuidelinesPage
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
