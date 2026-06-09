import ReactMarkdown from "react-markdown";

// Static help/guidelines page.  Content is plain markdown so it's easy to edit.
// Keep this in sync with guideline.md at the project root.
const GUIDE = `
# How to use the Academic Co-Pilot

Your AI research assistant for **finding literature, screening abstracts,
ingesting PDFs, planning & drafting cited papers, and analyzing data** — all from
one chat, with your approval on anything sensitive.

## 1. Upload your files
Use the **Files** panel on the left (drag-and-drop or browse). Supported types:

- **PDF** — ingest into the knowledge base so the agent can search, quote, and
  cite it when drafting.
- **CSV** — used for abstract screening and data analytics.

Files are saved per session, so different chats don't clash.

## 2. Reference a file in your message
You never have to remember file paths:

- Type **\`@\`** in the message box to open an autocomplete of your uploaded
  files, then pick one — its exact path is inserted for you.
- Or click **insert** next to any file in the Files panel.
- You can also just say *"my CSV"* — the agent knows the session's files.

## 3. Find & gather literature
- **Search new papers (arXiv):** *"Find recent arXiv papers on agentic RAG for
  legal compliance."*
- **Search indexed/peer-reviewed work (Scopus):** *"Search Scopus for the most
  cited papers on retrieval-augmented generation."* (Requires a server API key;
  full results may need your institution's access.)
- **Search your own ingested PDFs:** *"What do my papers say about evaluation
  methods?"* — returns the exact passages, grounded in your documents.
- **Summarize one PDF:** *"Summarize @paper.pdf"* — a structured TL;DR (problem,
  method, data, findings, limitations) without ingesting it.
- **Get a clean citation:** *"Give me the BibTeX for DOI 10.1145/3539618"* (or a
  title) — resolved via Crossref.

## 4. Plan, draft & export a paper
- **Plan:** *"Suggest titles / generate an outline / plan the sections for a paper
  on …"*
- **Draft sections:** *"Write the full paper section by section."* The agent drafts
  each section **one at a time**, pausing for your approval before each, and
  grounds empirical sections in your ingested PDFs and CSV data.
- **Export:** *"Compile the approved sections into a Word document."* You get a
  downloadable **.docx**.

## 5. Screen abstracts
*"Screen the abstracts in @… for papers about LLMs or RAG. Exclude medical
imaging. Save to an Excel file."* — produces a color-coded **.xlsx** (green =
keep, red = reject) with a justification per row. CSV needs \`title\` and
\`abstract\` columns.

## 6. Analyze data
*"Plot the distribution of decisions"* or *"compute summary stats for @data.csv"*
— the agent writes Python (pandas/matplotlib), runs it after your approval, and
shows charts right in the chat. Tip: it inspects column names first, so you don't
have to spell them out.

## 7. The agent's task plan
For multi-step jobs the agent writes itself an ordered **checklist** and ticks
steps off as it works — shown in the **Plan** panel. This keeps long jobs
(ingest → draft → chart → compile) on track even across approval pauses.

## 8. Approving sensitive actions
Tools that run code or change saved state **pause for your approval**: ingesting,
screening, drafting, analytics, and compiling. When you see the approval card:

- **Approve** — run it as proposed.
- **Edit args** — tweak the arguments (as JSON), then run.
- **Reject** — skip it, optionally telling the agent why.

(Read-only tools — all the searches, summaries, and citation lookups — run
instantly without interrupting you.)

## 9. Generated files
When the agent creates a chart, spreadsheet, or document, it appears in the chat
as a **clickable link** (charts render inline). Click to open or download.

## 10. Managing chats
- The **Chats** list (top-left) keeps your sessions. Click one to reload its full
  history.
- **Rename** (✎ or double-click), **delete** (✕), or start a **+ New** chat.
- Have a session key from elsewhere? Paste it into **"Open by key"** to load it.

---

*Tip: conversations are saved automatically — you can close the tab and come back
to pick up where you left off.*
`;

export default function GuidelinesPage({ onBack }) {
  return (
    <div className="guidelines-page">
      <div className="guidelines-inner md">
        <button className="ghost back-btn" onClick={onBack}>
          ← Back to chat
        </button>
        <ReactMarkdown>{GUIDE}</ReactMarkdown>
      </div>
    </div>
  );
}
