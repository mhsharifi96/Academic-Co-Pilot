# Academic Co-Pilot Skills

This file defines the skills (tools) available to the Academic Co-Pilot Agent.

> 🔒 **Human-in-the-loop:** Tools marked **[Requires Approval]** pause the agent and wait for an explicit approve / edit / reject decision before they run. These are the tools that execute code or modify persistent state.

## 1. Excel Screener (`screen_abstracts_csv`) **[Requires Approval]**
*   **Description:** Evaluates academic abstracts in a CSV file against specified inclusion criteria. Generates a color-coded Excel file with decisions and justifications.
*   **Inputs:**
    *   `csv_path` (str): Path to the input CSV file (must have 'title' and 'abstract' columns).
    *   `criteria` (str): Inclusion/exclusion criteria to screen against.
    *   `output_path` (Optional[str]): Path for the output Excel file.
    *   `feedback` (Optional[str]): Extra user considerations or specific instructions for screening.

## 2. Document Ingestor (`ingest_pdf`) **[Requires Approval]**
*   **Description:** Parses a local PDF file, chunks the text, generates OpenAI embeddings, and stores them in the PostgreSQL/pgvector database.
*   **Inputs:**
    *   `file_path` (str): The absolute path to the PDF file.

## 3. Title Suggester (`suggest_paper_titles`)
*   **Description:** Suggests original and catchy academic paper titles based on a topic and relevant documents retrieved from the vector database.
*   **Inputs:**
    *   `topic` (str): The research topic.
    *   `num_titles` (int, default=5): Number of titles to suggest.
    *   `feedback` (Optional[str]): Extra user considerations or specific style preferences for titles.

## 4. Paper Planner (`generate_paper_outline`)
*   **Description:** Generates a detailed, structured hierarchical outline (Introduction, Literature Review, Methodology, etc.) for a paper based on a topic and title.
*   **Inputs:**
    *   `topic` (str): The research topic.
    *   `title` (str): The selected paper title.
    *   `feedback` (Optional[str]): Extra user considerations or specific sections to include/emphasize.

## 5. RAG Drafter (`draft_paper_section`) **[Requires Approval]**
*   **Description:** Drafts a specific section of an academic paper using RAG over ingested PDFs and a specified citation style (IEEE, APA, Vancouver). Optionally grounds the draft in quantitative data from uploaded CSV files. Pauses for human approval before each section is written, which powers the section-by-section full-paper writing flow.
*   **Inputs:**
    *   `section_title` (str): The title of the section to draft.
    *   `outline` (str): The full paper outline for context.
    *   `citation_style` (Literal["IEEE", "APA", "Vancouver"], default="IEEE"): The desired citation style.
    *   `feedback` (Optional[str]): Extra user considerations or specific points to cover in this section.
    *   `data_files` (Optional[List[str]]): Session data file paths (CSV or .xlsx) whose data should inform this section. Provide for empirical sections (Results, Methodology); omit for narrative ones (Introduction, Conclusion).

## 6. Analytics Sandbox (`analytics_sandbox`) **[Requires Approval]**
*   **Description:** A secure Python sandbox for data analysis and visualization using pandas and matplotlib. Pre-imported and ready to use: `pd` (pandas), `np` (numpy), `plt` (matplotlib), `nx` (networkx, for graphs/networks), and `WordCloud` (for word-cloud images), plus common standard-library modules `re`, `json`, `math`, `statistics`, `datetime`, `collections`, `itertools`, `random`, and `Counter`/`defaultdict`. Saves plots to the `output_figures/` directory. Treat each call as a fresh environment — write self-contained scripts that re-read any CSV/Excel files (don't assume a variable like `df` survives from a previous call). If the code errors, the sandbox automatically inspects the error and retries with corrected code (up to 2 times) before reporting back.
*   **Inputs:**
    *   `code` (str): The Python code to execute.
    *   `feedback` (Optional[str]): Extra user considerations or specific constraints for the code execution.

## 7. CSV Inspector (`get_csv_info`)
*   **Description:** Reads a CSV file and returns its structure: column names, data types, row and column counts, and a preview of the first 5 rows. Always use this before writing analytics code to ensure correct column names and data types are used.
*   **Inputs:**
    *   `csv_path` (str): Path to the CSV file to inspect.

## 8. Session File Lister (`list_session_files`)
*   **Description:** Lists all files that have been uploaded and are available in the current user session. Use this when the user asks what files or data are available to work with.
*   **Inputs:**
    *   `session_id` (str): The current session ID.

## 9. Section Planner (`plan_paper_sections`)
*   **Description:** Parses a paper outline into a clean, ordered list of top-level section titles. Use this after generating an outline and before writing the full paper — iterate the returned list and call the RAG Drafter for each title in order so every section is covered exactly once.
*   **Inputs:**
    *   `outline` (str): The full paper outline (e.g. from `generate_paper_outline`).

## 10. Corpus Search (`search_my_papers`)
*   **Description:** Semantic search over the papers already ingested into the vector database. Returns the most relevant passages so you can gather evidence or check what the corpus says about a topic before drafting. Read-only (no approval).
*   **Inputs:**
    *   `query` (str): A question or topic to search for.
    *   `k` (int, default=5): Number of passages to return.

## 11. Paper Summarizer (`summarize_paper`)
*   **Description:** Produces a structured TL;DR of a single PDF (Problem / Method / Data / Key Findings / Limitations) without ingesting it into the vector database. Read-only (no approval).
*   **Inputs:**
    *   `file_path` (str): Path to the PDF file.
    *   `feedback` (Optional[str]): Optional focus or extra considerations for the summary.

## 12. Literature Search (`search_literature`)
*   **Description:** Searches arXiv (free, no API key) for academic papers matching a query. Use this to discover relevant literature that has NOT been uploaded yet — returns title, authors, year, arXiv id/link, and an abstract snippet. Read-only (no approval).
*   **Inputs:**
    *   `query` (str): Search terms.
    *   `max_results` (int, default=8): Maximum number of papers to return (capped at 25).

## 13. Citation Resolver (`resolve_citation`)
*   **Description:** Resolves a DOI or paper title to clean citation metadata (authors, year, venue, DOI) plus a BibTeX entry via Crossref (free, no API key). Use this to ground citations in real metadata instead of guessing. Read-only (no approval).
*   **Inputs:**
    *   `doi_or_title` (str): A DOI (e.g. `10.1145/3539618`) or a paper title.

## 14. Document Compiler (`compile_paper`) **[Requires Approval]**
*   **Description:** Assembles drafted sections into a single Word (.docx) document under `data/`, downloadable via the `/download` endpoint. Use after the user has approved the individual sections.
*   **Inputs:**
    *   `title` (str): The paper title (used as document heading and filename).
    *   `sections` (List[Dict]): Ordered sections, each `{"heading": str, "body": str}`.
    *   `output_path` (Optional[str]): Path for the .docx. Defaults to `data/<slug>.docx`.

## 15. Task Planner (`write_plan`, `update_plan`)
*   **Description:** A self-authored todo list for multi-step tasks. Call `write_plan` FIRST whenever a request needs several steps/tool calls (roughly 3+) to lay out an ordered checklist, then call `update_plan` to mark each step `in_progress`/`done` as you progress. The plan is stored per session (outside the chat history) and shown back to you at the start of every turn, so it survives history summarization and approval pauses. Read-only scratch memory (no approval); the `session_id` is supplied automatically. Skip planning for simple one-or-two-step requests.
*   **Inputs (`write_plan`):**
    *   `steps` (List[str]): Ordered, short step descriptions.
*   **Inputs (`update_plan`):**
    *   `step_index` (int): Zero-based index of the step to update.
    *   `status` (str): `in_progress`, `done`, or `pending`.

## 16. Scopus Search (`search_scopus`)
*   **Description:** Searches Elsevier's Scopus for peer-reviewed / indexed academic literature, including citation counts. Complements `search_literature` (arXiv preprints) by covering published, indexed work across publishers. Requires `ELSEVIER_API_KEY` on the server; reports a friendly message when unset. Plain keywords are matched against title/abstract/keywords; Scopus boolean syntax is also accepted. Read-only (no approval).
*   **Inputs:**
    *   `query` (str): Search terms or a Scopus boolean query.
    *   `max_results` (int, default=10): Maximum number of results (capped at 25).
