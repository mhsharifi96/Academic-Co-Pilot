# powerpoint.md — Presentation source for Academic Co-Pilot

This file is the **single source of truth for the product slide deck**. It is
written to be handed to Claude with a prompt like:

> Read `powerpoint.md` and generate the PowerPoint file.

Everything the generator needs — deck settings, brand colors, slide order,
per-slide copy, speaker notes, and the build command — is below. Edit this file
rather than editing a generated `.pptx`, then regenerate.

Content is derived from `feature.md` (the full feature catalogue). When a
feature changes, update `feature.md` first, then reflect it here.

---

## 1. How to generate the deck

The deck is built with **python-pptx**, which is not a project dependency — run
it through `uv` so nothing is added to `pyproject.toml`:

```bash
# Generate the .pptx from the build script
uv run --with python-pptx python scripts/build_deck.py

# Output
# dist/academic-co-pilot.pptx
```

If `scripts/build_deck.py` does not exist yet, the generator should create it:
a single script that reads the settings in §2 and the slides in §4 and writes
`dist/academic-co-pilot.pptx`. Keep the script deterministic — running it twice
must produce the same deck.

**Generator rules**

1. Slide size **16:9** (13.333in × 7.5in).
2. One slide per `### Slide N` heading in §4, in the order written.
3. `Title` becomes the title placeholder; `Bullets` become body bullets at the
   indent level shown; `Notes` go in the speaker-notes pane (never on the slide).
4. `Visual` is a direction for the presenter or designer. If a diagram is
   described, draw it with native pptx shapes when it is simple (boxes and
   arrows); otherwise leave a labelled placeholder rectangle.
5. Never invent features. If a bullet is unclear, take the wording from
   `feature.md` verbatim.
6. Maximum **6 bullets** per slide and roughly **12 words** per bullet. If a
   slide overflows, split it and renumber.

---

## 2. Deck settings

| Setting | Value |
|---|---|
| Title | Academic Co-Pilot |
| Subtitle | An agentic RAG assistant for researchers |
| Aspect ratio | 16:9 |
| Theme | Dark |
| Language | English (a Persian edition is described in §5) |
| Target length | 26 slides, ~25 minutes |
| Audience | Mixed — researchers who will use it, plus stakeholders evaluating it |

### Brand colors

Taken from `frontend/src/styles.css` so the deck matches the product.

| Role | Hex | Used for |
|---|---|---|
| Background | `#0F1117` | Slide background |
| Panel | `#171A23` | Cards, table fills, code blocks |
| Border | `#2A2F3C` | Hairlines, table borders |
| Text | `#E6E8EE` | Body copy |
| Muted | `#9AA3B2` | Captions, footers, secondary text |
| Accent | `#5B8CFF` | Titles, key numbers, emphasis, arrows |
| Success | `#2ECC71` | "Included" / positive states |
| Danger | `#FF5C6C` | Blocked / failed states |
| Warning | `#F5A623` | Pending / retry states |

### Typography

| Role | Font | Size |
|---|---|---|
| Slide title | Crimson Pro (fallback Georgia) | 36pt |
| Section divider | Crimson Pro | 44pt |
| Body bullet | Segoe UI (fallback Arial) | 20pt |
| Sub-bullet | Segoe UI | 16pt |
| Code / paths | Consolas | 16pt |
| Footer | Segoe UI | 11pt, muted |

Footer on every slide except the title: `Academic Co-Pilot · <section name>`
left-aligned, slide number right-aligned.

---

## 3. Narrative arc

The deck moves through five acts. Section dividers mark each one.

1. **The problem** (slides 1–3) — what a literature-to-manuscript workflow costs today.
2. **The system** (4–7) — two agents, one chat, persistent state.
3. **The capabilities** (8–19) — the feature tour, in the order a researcher meets them.
4. **The platform** (20–23) — safety, billing, administration, architecture.
5. **The close** (24–26) — deployment, limitations, ask.

---

## 4. Slides

### Slide 1 — Title
- **Layout:** Title
- **Title:** Academic Co-Pilot
- **Subtitle:** From raw PDFs to a cited manuscript — without leaving the chat
- **Visual:** Full-bleed dark background, accent rule under the title, product wordmark.
- **Notes:** One line to open: this is an agentic RAG assistant that takes a researcher from a folder of PDFs and CSVs to a screened spreadsheet, an outline, cited draft sections, charts, and a compiled `.docx`.

### Slide 2 — The problem
- **Layout:** Title and content
- **Title:** Research admin eats the research
- **Bullets:**
  - Screening hundreds of abstracts by hand, one spreadsheet row at a time
  - Citations copied by hand, and sometimes invented by a chatbot
  - Analysis lives in one tool, writing in another, sources in a third
  - Every new chat starts from zero — no memory of your corpus
- **Visual:** Four muted icons in a row, each with a one-word label.
- **Notes:** Frame the pain before the product. Each bullet maps to a capability shown later, so the audience can connect them.

### Slide 3 — What it does instead
- **Layout:** Title and content
- **Title:** One conversation, the whole pipeline
- **Bullets:**
  - Search Scopus, arXiv, Crossref and OpenAlex from the chat
  - Upload PDFs and CSVs — PDFs are embedded and searchable at once
  - Screen abstracts into a color-coded Excel decision sheet
  - Draft each section grounded in your own corpus, in IEEE / APA / Vancouver
  - Run Python on your data and get charts back inline
  - Compile the result into a downloadable `.docx`
- **Visual:** Left-to-right pipeline: Discover → Ingest → Screen → Draft → Analyse → Export. Accent arrows.
- **Notes:** This is the whole deck in one slide. Everything after it is detail.

### Slide 4 — Section divider
- **Layout:** Section header
- **Title:** The system
- **Visual:** Accent-on-dark divider, act number "02" in muted type.

### Slide 5 — Two agents, chosen per session
- **Layout:** Two content
- **Title:** Pick your agent before the first message
- **Bullets:**
  - **Academic agent** — LangChain 1.0 `create_agent`, optional approval gates
    - Strict section-by-section drafting protocol
  - **Deep research agent** — wraps `deepagents.create_deep_agent`
    - Fully autonomous: `write_todos` planning, virtual filesystem memory, no pauses
  - Both draw from the same tool registry
  - The choice is stored on the session and is immutable afterwards
- **Visual:** Two cards side by side, each with its badge; a shared "tools" bar underneath.
- **Notes:** The immutability is deliberate — `chat`, `resume`, `history` and `plan` all dispatch on `agent_type`, so a mid-run switch would corrupt the thread. A third focused `ScreenerAgent` exists for screening only.

### Slide 6 — Conversations that survive everything
- **Layout:** Title and content
- **Title:** Stateful, multi-session chat
- **Bullets:**
  - LangGraph `AsyncPostgresSaver` keyed by `thread_id == session_id`
  - Clients send only the new message — history reloads server-side
  - Sessions survive server restarts and browser reloads
  - History past ~4k tokens is auto-summarized, last 20 messages kept verbatim
  - Rename, reload, delete, or open a session by ID
- **Visual:** Timeline of a session crossing a "server restart" marker unbroken.
- **Notes:** Emphasise cost: summarization keeps long research sessions coherent *and* affordable without manual pruning.

### Slide 7 — The agent writes its own plan
- **Layout:** Title and content
- **Title:** A visible task checklist
- **Bullets:**
  - For multi-step requests the agent calls `write_plan`, then `update_plan`
  - Steps move through `pending` → `in_progress` → `done`
  - Stored per session **outside** the chat history, so summarization can't lose it
  - Replayed into every turn and shown live in the plan sidebar
  - Deep-agent sessions surface `write_todos` through the same endpoint
- **Visual:** Screenshot of `PlanSidebar.jsx` with two steps done, one in progress.
- **Notes:** This is the trust feature — the user can see what the agent intends to do before it does it, even with approval gates switched off.

### Slide 8 — Section divider
- **Layout:** Section header
- **Title:** The capabilities
- **Visual:** Divider, act number "03".

### Slide 9 — Literature discovery
- **Layout:** Title and content
- **Title:** Four catalogues, one search
- **Bullets:**
  - `search_literature` — Scopus first, then arXiv preprints, then Crossref
  - `search_scopus` — Scopus only, with citation counts and boolean syntax
  - `search_openalex` — ~250M works, open-access status and links
  - `resolve_citation` — DOI or title → clean metadata plus ready BibTeX
  - `suggest_venues` — ranked journals and conferences for your topic
- **Visual:** Four source logos feeding one result list.
- **Notes:** All searches are read-only, and general web browsing is deliberately out of scope. `resolve_citation` is what grounds citations in real metadata instead of guesses.

### Slide 10 — Document intake
- **Layout:** Title and content
- **Title:** Upload once, searchable immediately
- **Bullets:**
  - `POST /upload` takes multiple PDFs and CSVs at once
  - Validated as a batch — nothing is partially ingested
  - Stored under `data/<session_id>/`, so sessions never collide
  - PDFs are chunked, embedded, and written to pgvector automatically
  - CSVs are held for screening and analysis
- **Visual:** Drag-and-drop illustration → chunk grid → vector store cylinder.
- **Notes:** Collection name is `academic_papers`. The `@`-mention picker in the composer lets users insert exact file paths into a message.

### Slide 11 — Retrieval over your own corpus
- **Layout:** Title and content
- **Title:** Evidence before prose
- **Bullets:**
  - `search_my_papers` — semantic search returning the top-k relevant passages
  - `summarize_paper` — structured TL;DR of one PDF, without ingesting it
    - Problem / Method / Data / Key Findings / Limitations
  - The per-turn context message means the agent always knows which files exist
- **Visual:** Two-column comparison: "asks the model" vs "asks your corpus".
- **Notes:** `summarize_paper` deliberately skips the vector store so a quick triage read doesn't pollute the corpus.

### Slide 12 — The download queue
- **Layout:** Title and content
- **Title:** DOI in, ingested PDF out
- **Bullets:**
  - Paste a DOI, or click the `📄 Get PDF` chip the UI shows on any DOI in chat
  - A background worker drains the queue one job at a time
  - On success: saved, ingested, and attached to the session as future context
  - Statuses: `QUEUED` · `RUNNING` · `RETRY_SCHEDULED` · `SUCCEEDED` · `FAILED`
  - You keep chatting while jobs run; the UI polls every 4 seconds
- **Visual:** Queue diagram with three jobs in different colored states (amber, accent, green).
- **Notes:** Entirely frontend plus REST — no agent or tool changes were needed. `PROVIDER_TOKEN` is backend-only and never reaches the browser.

### Slide 13 — Fair queueing
- **Layout:** Title and content
- **Title:** Quota that stays fair under load
- **Bullets:**
  - 10 originating requests per user per rolling 24 hours
  - Retries and deduplicated DOIs **don't** consume quota
  - Requests 1–3 are FAST (~1h target); 4–10 are STANDARD, spread across 24h
  - Deterministic per-user jitter stops everyone firing at once
  - Anti-starvation: after several FAST jobs, an eligible STANDARD job runs
  - On `404` the job retries 3× (10 then 20 min) — the worker never sleeps
- **Visual:** 24-hour timeline with FAST jobs clustered at the front, STANDARD spread across.
- **Notes:** These are pure, unit-tested functions in `app/services/download_service.py`. If a job fails terminally, the chat offers "Upload PDF" or "Continue without PDF".

### Slide 14 — Screening
- **Layout:** Title and content
- **Title:** Abstracts in, decisions out
- **Bullets:**
  - `screen_abstracts_csv` takes a CSV with `title` and `abstract` columns
  - Evaluates every row against your inclusion/exclusion criteria
  - Produces a **color-coded Excel workbook**: decision plus justification per row
  - Optional `feedback` carries extra instructions into the pass
- **Visual:** Before/after — plain CSV rows on the left, green/red workbook on the right.
- **Notes:** This is often the first thing a systematic-review user tries, and the clearest single time saving in the product.

### Slide 15 — Planning and drafting
- **Layout:** Title and content
- **Title:** Title → outline → sections → draft
- **Bullets:**
  - `suggest_paper_titles` — N original titles, informed by your ingested corpus
  - `generate_paper_outline` — full hierarchical outline for topic and title
  - `plan_paper_sections` — parses the outline into an ordered section list
  - `draft_paper_section` — RAG draft per section in IEEE / APA / Vancouver
  - Empirical sections can be grounded in session CSV/XLSX data
- **Visual:** Four-stage vertical flow, each stage naming its tool in mono type.
- **Notes:** `plan_paper_sections` exists so each section is drafted exactly once — it is the guard against the agent looping or skipping.

### Slide 16 — The full-paper protocol
- **Layout:** Title and content
- **Title:** How a whole paper gets written
- **Bullets:**
  - Ensure an outline exists, then call `plan_paper_sections`
  - Draft sections **one at a time, in order**, each building on the last
  - `data_files` passed for empirical sections, omitted for narrative ones
  - Present the assembled paper, then offer to compile a `.docx`
  - With approval enabled this becomes approve / edit / reject **per section**
- **Visual:** Numbered 5-step flow, with an "approval gate" badge on step 5.
- **Notes:** The deep agent runs the same protocol autonomously. `compile_paper` assembles ordered `{heading, body}` sections into a Word file under `data/`, served through `/download`.

### Slide 17 — Quality tooling
- **Layout:** Title and content
- **Title:** Catching what AI writing gets wrong
- **Bullets:**
  - `validate_references` resolves every DOI and URL **over the network**
    - Flags dead links, fabricated entries, and unsupported in-text claims
  - `humanize_text` rewrites AI prose into natural writing
    - Meaning, facts, numbers and citations strictly preserved
  - `suggest_venues` ranks journals by where similar work was published
- **Visual:** A reference list with two entries flagged red, one amber.
- **Notes:** Both use the *powerful* model tier. Hallucinated citations are the single biggest credibility risk in AI-assisted writing — this is the direct answer to it.

### Slide 18 — Data analysis
- **Layout:** Title and content
- **Title:** A Python sandbox that fixes itself
- **Bullets:**
  - `get_csv_info` first — columns, dtypes, counts, and a 5-row preview
  - `analytics_sandbox` runs Python with `pd`, `np`, `plt`, `nx`, `WordCloud` ready
  - Plots are saved to `output_figures/` and rendered inline in the chat
  - Each call is a fresh environment — scripts re-read their own data
  - **Self-healing:** on an error it reads the traceback and retries up to 2×
- **Visual:** Code block on the left, resulting chart on the right.
- **Notes:** The `get_csv_info`-first rule is in the system prompt precisely because guessed column names are the most common failure. Be honest in Q&A: `PythonREPL` is not a hardened sandbox — approval gating is the guard.

### Slide 19 — Guided workflows (wizards)
- **Layout:** Title and content
- **Title:** For users who don't know what to ask
- **Bullets:**
  - Admin-authored, ordered multi-step flows run as a guided chat
  - Public bilingual catalogue at `#/` — browsable without signing in
  - Sticky stepper: "Step 2 of 5", progress bar, messages left in the step
  - A step ends three ways: the cap, your **Finish step**, or accepting the agent's suggestion
  - Uploads, suggested follow-up questions, and a live wallet chip in the header
  - **Five shipped workflows**, bilingual, seeded idempotently
- **Visual:** Screenshot of the wizard runner with the stepper and composer visible.
- **Notes:** There is no third agent — runs execute on the existing academic agent, with the step's guideline prompt arriving through the per-turn context so it survives summarization. The five: systematic review (6 steps), analyse your dataset, understand a paper deeply, write a research proposal, get ready to submit.

### Slide 20 — Section divider
- **Layout:** Section header
- **Title:** The platform
- **Visual:** Divider, act number "04".

### Slide 21 — Guardrails
- **Layout:** Title and content
- **Title:** Screened before it costs anything
- **Bullets:**
  - Rule layer — regexes catch common injection and jailbreak phrasings
  - Allow-list layer — short DOI and PDF commands recognised as in-scope
  - LLM classifier — a cheap model judges scope and abuse
  - Blocked messages return `status="blocked"` and are **not billed**
  - **Fails open** on classifier errors, so a transient fault can't take down chat
- **Visual:** Three-gate funnel, with the billing meter placed after the gates.
- **Notes:** Both agents also carry a non-negotiable "Scope & safety" section in their system prompts — including ignoring override attempts that arrive through *tool output*, not just user input. Toggle with `ENABLE_GUARDRAILS`.

### Slide 22 — Human-in-the-loop
- **Layout:** Title and content
- **Title:** Approve, edit, or reject — optional
- **Bullets:**
  - Off by default; `REQUIRE_TOOL_APPROVAL` gates the tools that act
  - Gated: sandbox, screening, ingestion, drafting, compiling, infographics, OA fetch
  - The graph pauses and `POST /chat` returns `status="interrupted"`
  - The UI renders an Approve / Edit / Reject card with the pending arguments
  - **Edit** re-runs the call with your corrected arguments
- **Visual:** Screenshot of `InterruptCard.jsx` with editable JSON args.
- **Notes:** When disabled, the agent runs its whole plan and returns only the final result — and the system prompt itself adapts to describe autonomous rather than approval-gated drafting.

### Slide 23 — Accounts, billing, administration
- **Layout:** Title and content
- **Title:** Metered per turn, managed from the browser
- **Bullets:**
  - JWT auth, bcrypt hashing, 7-day tokens; every route verifies session ownership
  - Cross-user access returns `404`, so session IDs aren't enumerable
  - Each turn's tokens are costed, deducted, and written to `usage_records`
  - Balance is returned on every reply and shown live in the header
  - Below the floor, chat returns **HTTP 402**; admins are never blocked
  - Admin console: balances, admin flags, and open/close registration at runtime
- **Visual:** Admin console screenshot with the balance column highlighted.
- **Notes:** The first account to register becomes admin, or set `ADMIN_EMAIL` to promote deterministically. Registration can be closed without a redeploy — and the very first account is always let through, so a fresh deployment can still bootstrap.

### Slide 24 — Architecture
- **Layout:** Title and content
- **Title:** One Postgres, three separate stores
- **Bullets:**
  - **App tables** — users, sessions, usage, download jobs (async SQLAlchemy / psycopg v3)
  - **Vector store** — PGVector + OpenAI embeddings, collection `academic_papers`
  - **Checkpointer** — LangGraph `AsyncPostgresSaver`; **chat messages live here**
  - `llm_repo` routes every model call through named tiers: `default`, `powerful`, image
  - Feature flags in `.env`, validated at import — the app won't start misconfigured
- **Visual:** Three labelled cylinders inside one Postgres boundary, with the driver named under each.
- **Notes:** The three-store split is the design decision most often misread. Swapping model or provider happens in exactly one file — `app/repositories/llm.py`.

### Slide 25 — Deployment and testing
- **Layout:** Title and content
- **Title:** Ships as Docker, tests without a network
- **Bullets:**
  - `docker-compose up --build` — Postgres/pgvector, API on `:8000`, UI on `:5173`
  - `docker-compose.prod.yml` + `run-prod.sh` for the production stack
  - `./run-prod.sh up | restart | rebuild | down | logs | ps`
  - Dependencies managed with **uv**; hot reload for both backend and frontend
  - `uv run pytest` runs **fully offline** — no network, no API keys
- **Visual:** Two columns: dev stack on the left, prod stack on the right.
- **Notes:** Tests cover HITL, guardrails, sessions, retrieval, literature search, the download scheduler, data grounding, the exporter, the reference checker, venue suggestions, the planner, the LLM repository, and deep-agent tool wiring.

### Slide 26 — Honest limits and what's next
- **Layout:** Title and content
- **Title:** What it doesn't do — yet
- **Bullets:**
  - Single-process assumptions: in-memory session state, one download worker
  - OpenAI-only today — `llm_repo` is the seam where that changes
  - No general web browsing; scoped scholarly lookups only
  - No Zotero or Mendeley integration
  - `analytics_sandbox` is a REPL, not a hardened sandbox
- **Visual:** Muted list, then a single accent line with the closing ask.
- **Notes:** Close by naming the limitations before the audience does — it buys credibility for everything claimed earlier. End with the specific ask for this audience (pilot users, budget, or a deployment slot).

---

## 5. Variants

**Short version (10 minutes, 12 slides).** Keep 1, 3, 5, 6, 9, 10, 14, 15, 17, 18, 19, 26. Drop the section dividers.

**Technical deep dive.** Keep the full deck and add detail slides after 24 for
the HITL resume protocol, the per-turn context message, and the wizard step
model. Source them from `CLAUDE.md` and `Design.md`.

**Persian edition.** The product ships bilingual (en/fa, RTL-aware). For a
Persian deck, translate titles, bullets and notes, set the body font to
**Vazirmatn**, and set paragraph direction to RTL with right alignment. Keep all
tool names, endpoint paths, environment variables and code identifiers in Latin
script, untranslated.

---

## 6. Assets to capture before generating

Screenshots referenced above. Capture at 16:9, dark theme, on a seeded demo account:

| Slide | Screenshot |
|---|---|
| 7 | Plan sidebar, two steps done and one in progress |
| 12 | Downloads tab with jobs in three different states |
| 14 | Color-coded screening workbook, ~10 rows |
| 18 | A sandbox reply with code and a rendered chart |
| 19 | Wizard runner, stepper and composer visible |
| 22 | Interrupt card with editable arguments |
| 23 | Admin console, users table |

Save them to `docs/deck-assets/` as `slide-<N>.png`. Where a screenshot is
missing, the generator should place a labelled placeholder rectangle rather than
skipping the slide.
