# Academic Co-Pilot — User Guideline

Your AI research assistant for **finding literature, screening abstracts,
ingesting PDFs, planning & drafting cited papers, and analyzing data** — all from
one chat, with your approval on anything sensitive.

> This is the user-facing guide. The same content is shown in-app on the
> **Guidelines** page (`frontend/src/components/GuidelinesPage.jsx`) — keep the two
> in sync. For architecture/dev docs see `CLAUDE.md`, `Design.md`, and `PRD.md`.

---

## 1. Upload your files
Use the **Files** panel (drag-and-drop or browse). Supported types:

- **PDF** — ingest into the knowledge base so the agent can search, quote, and
  cite it when drafting.
- **CSV** — used for abstract screening and data analytics. Screening CSVs must
  have `title` and `abstract` columns.

Files are saved per session, so different chats don't clash.

## 2. Reference a file in your message
You never have to remember file paths:

- Type **`@`** in the message box to autocomplete your uploaded files; pick one
  and its exact path is inserted.
- Or click **insert** next to any file in the Files panel.
- Or just say *"my CSV"* — the agent knows the session's files.

## 3. Find & gather literature

| Goal | Try saying | Notes |
|------|------------|-------|
| Discover new preprints | *"Find arXiv papers on agentic RAG."* | arXiv, free |
| Find indexed / cited work | *"Search Scopus for the most cited RAG papers."* | Needs `ELSEVIER_API_KEY`; full results may require institutional access |
| Query your own PDFs | *"What do my papers say about evaluation?"* | Grounded in your ingested documents |
| Summarize one PDF | *"Summarize @paper.pdf"* | Structured TL;DR, no ingestion needed |
| Get a citation | *"BibTeX for DOI 10.1145/3539618"* | Resolved via Crossref |

## 4. Plan, draft & export a paper
1. **Plan:** *"Suggest titles / generate an outline / plan the sections for a paper
   on …"*
2. **Draft:** *"Write the full paper section by section."* The agent drafts each
   section **one at a time**, pausing for approval before each, grounding empirical
   sections (Methodology, Results) in your ingested PDFs and CSV data.
3. **Export:** *"Compile the approved sections into a Word document."* → downloadable
   **.docx**.

## 5. Screen abstracts
*"Screen the abstracts in @… for papers about LLMs or RAG. Exclude medical
imaging."* → a color-coded **.xlsx** (green = keep, red = reject) with a
justification per row.

## 6. Analyze data
*"Plot the distribution of decisions"* or *"summary stats for @data.csv"* — the
agent writes and runs Python (pandas/matplotlib) after your approval, and shows
charts inline. It inspects column names first, so you don't have to spell them out.

## 7. The agent's task plan
For multi-step jobs the agent writes itself an ordered **checklist** and ticks
steps off as it works (shown in the **Plan** panel). This keeps long jobs
(ingest → draft → chart → compile) on track across approval pauses and history
summarization.

## 8. Approving sensitive actions (Human-in-the-Loop)
Tools that **run code or change saved state** pause for your approval:
`ingest_pdf`, `screen_abstracts_csv`, `draft_paper_section`, `analytics_sandbox`,
and `compile_paper`. On the approval card you can:

- **Approve** — run as proposed.
- **Edit args** — tweak the arguments (JSON), then run.
- **Reject** — skip it, optionally explaining why.

All **read-only** tools — every search, summary, and citation lookup — run
instantly without interrupting you.

## 9. Generated files
Charts, spreadsheets, and documents appear in the chat as **clickable links**
(charts render inline). Click to open or download.

## 10. Managing chats
- The **Chats** list keeps your sessions; click one to reload its full history.
- **Rename** (✎ or double-click), **delete** (✕), or start a **+ New** chat.
- Paste a session key into **"Open by key"** to load a chat from elsewhere.

---

## Tips for best results
- **Be specific** — *"screen for RCTs on diabetes published after 2020"* beats
  *"screen these."*
- **Give it your data first** — upload/ingest before asking; grounding prevents
  hallucinated citations.
- **Use Edit, not Reject** — when an approval card appears, tweak the proposed
  args rather than rejecting and re-explaining.
- **Iterate** — the agent remembers the thread, so *"now make the chart blue"*
  works without repeating context.

*Conversations are saved automatically — close the tab and come back anytime.*
