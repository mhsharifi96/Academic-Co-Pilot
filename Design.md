# Design / Architecture

Technical design of the Academic Co-Pilot backend. Pairs with `PRD.md` (what/why)
and `project_structure.md` (where).

## Tech stack
- **API:** FastAPI (async), Pydantic v2 schemas, Swagger at `/docs`.
- **Agent:** LangChain 1.0 `create_agent` (a LangGraph state machine) + middleware.
- **LLM:** OpenAI via `langchain-openai` (`OPENAI_MODEL`, `temperature=0`).
- **Data:** PostgreSQL + pgvector.
- **Auth:** JWT bearer + bcrypt.
- **Tracing:** LangSmith (optional).
- **Packaging/Deploy:** uv, Docker Compose (db + app + nginx-served React UI).

## High-level diagram
```
React SPA ──HTTP /api──> FastAPI routers ──> AcademicAgent (singleton on app.state)
                              │                     │
                              │                     ├─ SummarizationMiddleware
                              │                     ├─ HumanInTheLoopMiddleware ──(interrupt)──┐
                              │                     └─ tools (@tool)                           │
                              │                                                                │
                    SessionManager (in-mem: files + pending interrupt) <───────────────────────┘
                              │
        ┌─────────────────────┼───────────────────────────────┐
   App tables             Vector store                  Checkpointer
 (psycopg v3 async)   (PGVector, psycopg2 sync)   (AsyncPostgresSaver)
 users, chat_sessions   academic_papers           conversation messages
        └──────────────── all on the same Postgres instance ───┘
```

## Key design decisions

### 1. Single shared agent
`app/main.py` `lifespan` opens the checkpointer, builds **one** `AcademicAgent`
on top of it, and stores it on `app.state.agent`. Rationale: the Postgres saver
holds a connection pool whose lifecycle must be owned centrally; rebuilding the
agent per request would be wasteful and would leak connections.

### 2. Three separate Postgres-backed stores (deliberately distinct)
Same database, three independent subsystems — **do not conflate them**:
| Store | Module | Driver | Holds |
|-------|--------|--------|-------|
| App tables | `core/database.py` | psycopg **v3** async (`postgresql+psycopg://`) | users, chat-session ownership |
| Vector store | `core/db.py` | psycopg2 **sync** (PGVector) | paper embeddings (`academic_papers`) |
| Checkpointer | `core/checkpointer.py` | LangGraph AsyncPostgresSaver | **conversation messages** |

Chat history lives in the checkpointer, **not** in the app tables. Without
`DATABASE_URL`, the checkpointer falls back to `InMemorySaver` (tests/local).

### 3. Stateful chat via checkpointer
State is keyed by `thread_id == session_id == ChatSession.id`. The client sends
only the new message; LangGraph reloads prior context. `BaseAgent.run()` runs one
turn; `BaseAgent.resume()` continues a paused graph with `Command(resume=...)`.

### 4. Two "session" concepts (don't confuse)
- **`ChatSession`** (DB row): ownership, title, timestamps. CRUD in `session_service.py`.
- **`SessionManager`** (in-memory singleton, `core/sessions.py`): uploaded file
  paths + the pending HITL interrupt. Not persisted. `sync_get_files` lets
  synchronous `@tool` functions read files without deadlocking the asyncio lock
  (runs the coroutine in a worker thread when a loop is already running).

### 5. Human-in-the-loop (HITL)
`HumanInTheLoopMiddleware` gates `INTERRUPT_TOOLS` =
`{analytics_sandbox, screen_abstracts_csv, ingest_pdf, draft_paper_section}`.
- Gated tool requested → graph pauses with `__interrupt__`; `/chat` returns
  `status="interrupted"` + payload (via `extract_interrupt`); interrupt stashed
  in `SessionManager`.
- Client `POST /chat/resume` with `approve` / `edit` (+`edited_args`) /
  `reject` (+`reason`). `build_resume_command_value` maps this to
  `{"decisions": [...]}` (one per pending action) for the middleware.

### 6. Per-turn file context injection
The session's current file list is injected as a `SystemMessage` **each turn**
(`_build_context_message` → `run(context_message=...)`), not baked into the
static prompt — the file set changes between requests. This is also a token/cost
lever: only the live file list is sent, not the whole history (the checkpointer
+ summarization handle history).

### 7. Conversation summarization (cost control)
`SummarizationMiddleware` compresses history once it exceeds ~4k tokens while
keeping the last 20 messages verbatim — bounds context size and cost on long chats.

### 8. System prompt = static prompt + `skills.md`
`AcademicAgent` loads `skills.md` from CWD at construction and embeds it in the
system prompt, plus the strict section-by-section full-paper drafting protocol
(outline → plan sections → draft one at a time, each gated). Keep `skills.md` in
sync with the registered tools.

### 9. Auth & ownership
`get_current_user` (JWT bearer) protects endpoints; bcrypt passwords truncated to
72 bytes deliberately. Every session-scoped request verifies the user **owns**
the session (cross-user access → 404).

## Extensibility
Adding a tool is low-friction: write a `@tool`, append to the `AcademicAgent`
tool list, document in `skills.md`, and (if it executes code / mutates state)
add it to `INTERRUPT_TOOLS`. No router or graph changes needed.

## Known limitations
- `SessionManager` is in-process → single-worker assumption for file/interrupt state.
- OpenAI-only; model set via `OPENAI_MODEL`.
- `analytics_sandbox` uses `PythonREPL` (not a hardened sandbox) — HITL approval
  is the safety boundary.
