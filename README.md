# Academic Co-Pilot (PaperAgent)

An end-to-end, agentic RAG backend designed to accelerate academic research workflows. This system uses specialized LangChain agents to help researchers screen literature, ingest documents, plan papers, draft sections with citations, and perform data analysis in a secure sandbox.

## 🚀 Core Features

*   **Stateful Multi-Session Chat:** Each user gets a unique session. Conversation state is persisted automatically by a **LangGraph checkpointer** keyed by `session_id` — you send only the new message and the agent recalls the full history. No manual replay.
*   **Conversation Summarization:** A **SummarizationMiddleware** automatically compresses long histories once they exceed the token budget, keeping recent turns verbatim — long chats stay coherent and affordable.
*   **Human-in-the-Loop (HITL) Approvals:** Sensitive tools (code execution, screening, DB ingestion) pause and wait for your **approve / edit / reject** decision before running, via a dedicated `/chat/resume` endpoint.
*   **Multi-File Upload:** Upload multiple PDFs and CSVs in a single request. All files are automatically associated with your session.
*   **Excel Screener:** Automatically evaluates paper abstracts against specific inclusion/exclusion criteria. Generates color-coded Excel reports (Green for Keep, Red for Reject) with LLM justifications.
*   **Document Ingestor:** Seamlessly uploads and parses local PDF files, chunks the text, and stores semantic embeddings in a high-performance vector database.
*   **Research Planner:** Suggests catchy, relevant paper titles and generates structured, hierarchical outlines based on the knowledge stored in your database.
*   **RAG-Powered Drafter:** Drafts high-quality paper sections using Retrieval-Augmented Generation. Supports automatic citation formatting in **IEEE, APA, or Vancouver** styles.
*   **Analytics Sandbox:** A secure Python environment where the agent can write and execute pandas/matplotlib code to visualize research data and generate charts (`.png` output).
*   **CSV Inspector:** Ask the agent to inspect any uploaded CSV — it will show you column names, data types, and a preview before writing any analysis code.
*   **Session File Awareness:** The agent always knows which files you've uploaded. Just say "analyze my CSV" or "draft from my PDFs" and it finds them automatically.

## 🛠 Tech Stack

*   **API Framework:** [FastAPI](https://fastapi.tiangolo.com/)
*   **LLM Orchestration:** [LangChain 1.0](https://www.langchain.com/) `create_agent` + [LangGraph](https://langchain-ai.github.io/langgraph/) (checkpointer for state, middleware for summarization & human-in-the-loop)
*   **Package Management:** [uv](https://github.com/astral-sh/uv) (Extremely fast Python dependency resolver)
*   **Vector Database:** PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
*   **Observability:** [LangSmith](https://www.langchain.com/langsmith) (Integrated for agent tracing and debugging)
*   **Containerization:** Docker & Docker Compose

## 🏁 Getting Started

### 1. Prerequisites
*   [Docker](https://www.docker.com/) and Docker Compose installed.
*   An [OpenAI API Key](https://platform.openai.com/).

### 2. Configuration
Create a `.env` file in the root directory and populate it based on `.env.example`:

```env
# Core
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://postgres:postgres@db:5432/paper_agent

# LangSmith (Optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__your-key-here
LANGCHAIN_PROJECT=paper-agent
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### 3. Launch the System
Run the following command to build and start the application:

```bash
docker-compose up --build
```

This starts three services: the database, the API, and the **web UI**.

*   **Web UI:** `http://localhost:5173`
*   **API:** `http://localhost:8000` (interactive Swagger docs at `http://localhost:8000/docs`)

The UI container (nginx) reverse-proxies `/api` to the backend on the compose
network, so no CORS configuration is needed when running via Docker.

## 🖥️ Web UI

A React single-page app in `frontend/` provides a friendly chat interface over the
API — no more hand-written `curl`. It handles sessions for you, lets you upload
files by drag-and-drop, and renders the human-in-the-loop approvals as
**Approve / Edit / Reject** buttons.

**Reference a file with `@`-mentions.** Uploaded files are saved under `data/`,
but you never need to remember the path: type `@` in the message box and pick the
file from the autocomplete — its exact path (e.g. `data/abstracts.csv`) is inserted
into your prompt. (You can also just say "my CSV"; the agent already knows your
session's files.)

### Run the UI with Docker (recommended)

`docker-compose up --build` already builds and serves the UI at
`http://localhost:5173` (nginx serves the production bundle and proxies `/api` to
the backend). Nothing else to do.

### Run the UI in development (hot reload)

For live-reloading while editing the frontend, run the Vite dev server directly.
Start the backend first (see *Launch the System*, or `uv run uvicorn app.main:app
--reload`), then:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to the backend on
`:8000` (configured in `frontend/vite.config.js`), so no CORS setup is needed.

> Note: run **either** the Docker `frontend` service **or** the local Vite dev
> server — both use port `5173`.

## 🔌 API Endpoints

*   **`POST /api/v1/chat`**: The main chat interface. Send any research-related request with an optional `session_id` to continue a conversation. The `AcademicAgent` autonomously chooses the right tool.
    *   Body: `{"message": "...", "session_id": "..." (optional)}`
    *   Returns: `{"response": "...", "session_id": "...", "status": "complete" | "interrupted", "interrupt": {...} | null}`
    *   When `status` is `"interrupted"`, the agent is waiting for you to approve a sensitive tool — see `/chat/resume`.

*   **`POST /api/v1/chat/resume`**: Deliver a human-in-the-loop decision for a tool call awaiting approval.
    *   Body: `{"session_id": "...", "decision": "approve" | "edit" | "reject", "edited_args": {...} (for edit), "reason": "..." (optional, for reject)}`
    *   Returns: the same `ChatResponse` shape (a resume can itself hit another approval).

*   **`POST /api/v1/upload`**: Upload one or more PDF/CSV files. Pass an optional `session_id` to associate the files with a chat session.
    *   Form data: `files` (multiple), `session_id` (optional)
    *   Returns: `{"message": "...", "session_id": "...", "files": [{...}]}`

*   **`GET /api/v1/sessions/{session_id}/files`**: List the files associated with a session. Used by the Web UI to populate the file sidebar and the `@`-mention autocomplete (survives a page reload).
    *   Returns: `{"session_id": "...", "files": [{"path": "...", "filename": "...", "type": "pdf" | "csv"}]}`

## 📖 Usage Examples (Manual Testing)

### 1. Start a New Chat Session
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello! What can you help me with?"}'
```
**Expected:** Returns a greeting with a newly generated `session_id`. Save this ID for the next steps.

### 2. Upload Multiple Files (PDFs + CSVs)
```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
     -F "files=@data/abstracts.csv" \
     -F "files=@data/2406.16937v2.pdf" \
     -F "files=@data/10.1109_access.2024.3404862_mwuu.pdf" \
     -F "session_id=my-test-session"
```
**Expected:** Returns per-file results showing CSV saved and PDFs ingested into the vector store. The session `my-test-session` now has 3 files.

### 3. Ask What Files Are Available
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "What files do I have available in this session?", "session_id": "my-test-session"}'
```
**Expected:** The agent calls `list_session_files` and reports all 3 uploaded files by name.

### 4. Inspect a CSV Before Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Inspect the abstracts.csv file and show me its columns and a preview.", "session_id": "my-test-session"}'
```
**Expected:** The agent calls `get_csv_info` and returns column names, data types, row count, and the first 5 rows.

### 5. Screen Abstracts from CSV — triggers Human-in-the-Loop
`screen_abstracts_csv` is a gated tool, so this call **pauses for approval**:
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Screen the abstracts in data/abstracts.csv for papers about LLMs or RAG systems. Exclude medical imaging papers. Save to data/screened.xlsx.", "session_id": "my-test-session"}'
```
**Expected:** Response has `"status": "interrupted"` and an `interrupt` payload listing the `screen_abstracts_csv` call and its args. Nothing has run yet.

**Approve it** to actually run the screening:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/resume" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "my-test-session", "decision": "approve"}'
```
**Expected:** `"status": "complete"`, `data/screened.xlsx` generated with color-coded decisions and justifications.

### 6. Create a Chart from CSV Data — approve, edit, or reject
`analytics_sandbox` is also gated. First ask:
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Read data/screened.xlsx, count KEEP vs REJECT decisions, and create a bar chart saved to output_figures/screening_stats.png.", "session_id": "my-test-session"}'
```
**Expected:** `"status": "interrupted"` with the proposed Python `code` in the interrupt args.

**Reject** the run (the agent will not execute the code):
```bash
curl -X POST "http://localhost:8000/api/v1/chat/resume" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "my-test-session", "decision": "reject", "reason": "Use a pie chart instead."}'
```

**Or approve** to generate the chart at `output_figures/screening_stats.png`:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/resume" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "my-test-session", "decision": "approve"}'
```

### 7. Draft a Single Section Referencing Uploaded PDFs — gated
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Using the PDFs I uploaded, draft an Introduction section about multi-agent RAG systems. Use IEEE citation style.", "session_id": "my-test-session"}'
```
**Expected:** `draft_paper_section` is approval-gated, so the response is `"status": "interrupted"`. Approve via `/chat/resume` to retrieve relevant chunks from the vector store and produce a section with IEEE-formatted citations referencing the ingested papers.

### 8. Continue a Conversation (Multi-Turn)
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Now suggest 5 catchy paper titles based on the same topic and my uploaded papers.", "session_id": "my-test-session"}'
```
**Expected:** The agent remembers the previous context ("same topic") and suggests titles referencing the ingested PDFs.

### 9. Plan a Full Paper Outline
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Take the first title you suggested and generate a full hierarchical outline for the paper.", "session_id": "my-test-session"}'
```
**Expected:** The agent references the previous message and generates a structured outline.

### 9b. Write the Full Paper — Section by Section with Per-Section Approval
This is the flagship flow. Ask the agent to write the whole paper; it plans the
sections and then drafts them **one at a time**, pausing for your approval before
each one. CSV data is woven into empirical sections (Methodology/Results).

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Write the full paper section by section, grounded in my uploaded PDFs and the screening data in data/screened.xlsx. Use IEEE citations.", "session_id": "my-test-session"}'
```
**Expected:** The agent calls `generate_paper_outline` (if needed) and `plan_paper_sections`, then returns `"status": "interrupted"` for the **first** section (`draft_paper_section`, e.g. *Introduction*).

**Approve each section** to draft it and advance to the next:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/resume" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "my-test-session", "decision": "approve"}'
```
**Expected:** The section is written (citing the PDFs); the response then interrupts again for the **next** section. Repeat approve until every section is done.

**Steer a section** by editing its draft args instead of plain-approving — e.g. for a Results section, force it to use the CSV data and stay concise:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/resume" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "my-test-session", "decision": "edit", "edited_args": {"section_title": "Results", "feedback": "Report the KEEP vs REJECT counts from the screening data and keep it under 250 words.", "data_files": ["data/abstracts.csv"]}}'
```

**Reject a section** to have the agent adapt or skip it:
```bash
curl -X POST "http://localhost:8000/api/v1/chat/resume" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "my-test-session", "decision": "reject", "reason": "Merge this into the Discussion section instead."}'
```
**Expected after the last section:** `"status": "complete"` and the agent presents the assembled full paper in order.

### 10. Create a Scatter Plot from CSV Data
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "Load data/abstracts.csv and create a scatter plot showing the relationship between numeric columns (if any). Save to output_figures/scatter.png.", "session_id": "my-test-session"}'
```
**Expected:** The agent inspects the CSV, then proposes sandbox code and returns `"status": "interrupted"`. Approve via `/chat/resume` to generate the plot.

## 📂 Project Structure

```text
├── app/
│   ├── agents/       # create_agent setup, base/academic agents, HITL config (hitl.py)
│   ├── api/          # FastAPI routers and Pydantic schemas
│   ├── core/         # Config, Database, Sessions (file + interrupt tracking)
│   ├── tools/        # Custom LangChain tool implementations
│   └── main.py       # API Entrypoint
├── frontend/         # React (Vite) single-page web UI
├── data/             # Shared directory for CSVs and PDFs
├── output_figures/   # Generated research charts/plots
├── pyproject.toml    # Project metadata and dependencies (uv)
└── skills.md         # Central registry of agent capabilities
```

## 📜 Agent Skills
The agent's capabilities are dynamically defined in `skills.md`. Adding a new skill is as simple as creating a new `@tool` in `app/tools/` and registering it to the `AcademicAgent`.

## 🔄 Sessions, State & Human-in-the-Loop

State is keyed by `session_id` and persists for the lifetime of the API process (in-memory):

- **Conversation history** is owned by a **LangGraph `InMemorySaver` checkpointer** (`thread_id == session_id`). You send only the new message each turn; the agent reloads the full history automatically. No replay needed.
- **Conversation summarization** — once a thread's history exceeds ~4k tokens, `SummarizationMiddleware` summarizes older turns while keeping the 20 most recent messages verbatim, so long chats stay within budget.
- **Uploaded files** are tracked separately (`app/core/sessions.py`) and injected into the agent's context each turn so it knows which PDFs/CSVs belong to your session.

To continue a conversation, pass the same `session_id`. To start fresh, omit it (a new one is generated) or pass a new value.

### Human-in-the-Loop flow

The tools `analytics_sandbox`, `screen_abstracts_csv`, and `ingest_pdf` are gated by `HumanInTheLoopMiddleware`. When the agent wants to run one:

1. `POST /chat` returns `"status": "interrupted"` with an `interrupt.pending_actions` list (tool name + args).
2. You decide via `POST /chat/resume`:
   - `{"decision": "approve"}` — run as proposed.
   - `{"decision": "edit", "edited_args": {...}}` — run with your edited args.
   - `{"decision": "reject", "reason": "..."}` — skip the tool; the reason is fed back to the agent.
3. The resume returns either a `"complete"` response or another `"interrupted"` one (if the agent queued more gated calls).

---

## License

This project is licensed under the **[PolyForm Noncommercial License 1.0.0](LICENSE)** — © 2026 mhsharifi96.

You may use, modify, and share it freely for **any noncommercial purpose** (personal projects, study, research, education, non-profits). **Commercial use is not permitted** under this license. See the [LICENSE](LICENSE) file for the full terms.

---
*Built with ❤️ for the research community.*
