# Product Requirements Document — Academic Co-Pilot (PaperAgent)

## 1. Overview
An end-to-end agentic RAG assistant that accelerates academic research workflows.
A single conversational agent autonomously screens literature, ingests papers,
plans and drafts manuscripts with citations, and runs data analysis — all behind
a chat interface with human approval on sensitive actions.

## 2. Problem
Researchers juggle many disconnected tools to screen abstracts, manage PDFs,
outline papers, draft cited sections, and analyze data. Context is lost between
steps, and LLM tools that execute code or write files are risky to run unattended.

## 3. Goals
- One agent that picks the right tool from a natural-language request.
- Conversation state persisted per session (survives restarts) with no manual
  history replay by the client.
- Long conversations stay coherent and affordable via automatic summarization.
- Sensitive actions (code execution, DB writes, file generation) require explicit
  human approval before running.
- Per-user isolation: each user only sees and resumes their own sessions.

## 4. Non-Goals
- Multi-tenant scaling / horizontal session sharing (in-memory file state is per-process).
- Non-OpenAI model providers (current build is OpenAI-only).
- Reference-manager integrations (Zotero/Mendeley).
- General-purpose web browsing/search. (Scoped, read-only scholarly lookups are
  now supported — arXiv search via `search_literature` and Crossref metadata via
  `resolve_citation` — but open-ended web search remains out of scope.)

## 5. Users
Academic researchers and graduate students conducting literature reviews and
writing papers, working locally (Docker) with their own OpenAI key.

## 6. Core Features (functional requirements)

| # | Feature | Tool(s) | Approval |
|---|---------|---------|----------|
| F1 | Stateful multi-session chat | (agent + checkpointer) | — |
| F2 | Conversation summarization | SummarizationMiddleware | — |
| F3 | Multi-file upload (PDF/CSV) | `/upload` | — |
| F4 | Abstract screening → color-coded Excel | `screen_abstracts_csv` | ✅ |
| F5 | PDF ingestion into vector DB | `ingest_pdf` | ✅ |
| F6 | Title suggestions & outline generation | `suggest_paper_titles`, `generate_paper_outline`, `plan_paper_sections` | — |
| F7 | RAG section drafting w/ IEEE/APA/Vancouver citations | `draft_paper_section` | ✅ |
| F8 | Python analytics sandbox (charts → PNG) | `analytics_sandbox` | ✅ |
| F9 | CSV inspection before analysis | `get_csv_info` | — |
| F10 | Session file awareness ("analyze my CSV") | `list_session_files` + per-turn context | — |
| F11 | Full-paper writing, section-by-section with approval each | drafting protocol | ✅ |
| F12 | User auth (register/login) + per-user session ownership | JWT | — |
| F13 | Semantic search over the ingested corpus | `search_my_papers` | — |
| F14 | Structured TL;DR of a single PDF | `summarize_paper` | — |
| F15 | Discover new literature on arXiv | `search_literature` | — |
| F16 | Resolve DOI/title → metadata + BibTeX (Crossref) | `resolve_citation` | — |
| F17 | Compile approved sections into a .docx | `compile_paper` | ✅ |

## 7. Key User Flows
1. **Screen abstracts:** upload CSV → ask to screen against criteria → agent
   pauses for approval → approve → color-coded `.xlsx` produced.
2. **Draft a paper:** ingest PDFs → generate outline → draft each section
   (approve/edit/reject per section) → assembled paper.
3. **Analyze data:** upload CSV → `get_csv_info` → request a chart → approve
   proposed Python → PNG saved to `output_figures/`.

## 8. Requirements on sensitive actions (HITL)
Any tool that executes arbitrary code, writes to disk, or mutates the database
MUST interrupt and await an `approve` / `edit` / `reject` decision before running.
See `Design.md` for the mechanism.

## 9. Constraints / Assumptions
- Local-first; runs entirely in Docker Compose.
- Requires an OpenAI API key; LangSmith tracing optional but supported.
- PostgreSQL + pgvector is the single datastore (3 logical stores, see Design.md).
- CSVs for screening must have `title` and `abstract` columns.

## 10. Success Criteria
- A user can go from raw PDFs/CSV to a screened Excel, an outline, drafted cited
  sections, and a chart — without leaving the chat or losing context.
- No gated tool ever executes without explicit user approval.
- Sessions and history survive a server restart (Postgres-backed checkpointer).
