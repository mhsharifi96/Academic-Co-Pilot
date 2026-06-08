import ReactMarkdown from "react-markdown";

// Static help/guidelines page.  Content is plain markdown so it's easy to edit.
const GUIDE = `
# How to use the Academic Co-Pilot

Your AI research assistant for **literature screening, document ingestion, paper
planning, RAG-based drafting, and data analytics**.

## 1. Upload your files
Use the **Files** panel on the left (drag-and-drop or browse). Supported types:

- **PDF** — automatically ingested into the knowledge base so the agent can cite
  and quote them when drafting.
- **CSV** — used for abstract screening and data analytics.

Files are saved per session, so different chats don't clash.

## 2. Reference a file in your message
You never have to remember file paths:

- Type **\`@\`** in the message box to open an autocomplete of your uploaded
  files, then pick one — its exact path is inserted for you.
- Or click **insert** next to any file in the Files panel.
- You can also just say *"my CSV"* — the agent knows the session's files.

## 3. What you can ask
- **Screen abstracts:** *"Screen the abstracts in @… for papers about LLMs or RAG.
  Exclude medical imaging. Save to an Excel file."*
- **Plan a paper:** *"Suggest titles / generate an outline / plan the sections for
  a paper on …"*
- **Draft sections:** *"Write the full paper section by section."* Each section
  pauses for your approval before it's written.
- **Analyze data:** *"Plot the distribution of decisions"* — charts are generated
  and shown right in the chat.

## 4. Approving sensitive actions
Some tools (screening, ingesting, drafting, running analytics code) **pause for
your approval**. When you see the approval card, you can:

- **Approve** — run it as proposed.
- **Edit args** — tweak the arguments (as JSON), then run.
- **Reject** — skip it, optionally telling the agent why.

## 5. Generated files
When the agent creates a chart or spreadsheet, it appears in the chat as a
**clickable link** (charts render inline). Click to open or download.

## 6. Managing chats
- The **Chats** list (top-left) keeps your sessions on this device. Click one to
  reload its full history.
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
