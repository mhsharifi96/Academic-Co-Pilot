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
*   **Description:** A secure Python sandbox for data analysis and visualization using pandas and matplotlib. Saves plots to the `output_figures/` directory.
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
