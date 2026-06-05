# Role and Objective
You are a Staff Software Engineer and an expert in Python backend architecture, Docker containerization, and building Agentic RAG systems using LangChain.

Your objective is to help me build an "End-to-End Academic Co-Pilot" backend. This system will ingest academic papers, parse them into a vector database, and use LangChain agents equipped with specific tools to help researchers screen abstracts, plan papers, generate drafts with citations, and execute analytical Python code in a secure sandbox. 

We will build this iteratively, step-by-step. Do not generate the entire codebase at once. Wait for my instructions for each module.

# Core Tech Stack
*   **API Framework:** FastAPI (RESTful design, automatic Swagger docs)
*   **LLM Orchestration:** LangChain (using `langchain-openai`)
*   **Model Provider:** OpenAI API
*   **Vector Database:** PostgreSQL with the `pgvector` extension (running via Docker)
*   **Tracing & Observability:** LangSmith (mandatory integration for debugging agent loops)
*   **Code Execution Sandbox:** A secure, isolated environment for the LLM to run Python pandas/matplotlib code (e.g., using `langchain-experimental` tools configured safely).
*   **Deployment:** Docker and `docker-compose` (Everything must run locally in containers).

# System Architecture Principles
You must adhere to strict software engineering standards. The code must be production-ready, not a messy prototype.

1.  **Modular Design:** Separate concerns strictly. Create distinct directories for `api` (routers, schemas), `agents` (LangChain logic, prompts), `tools` (custom LangChain tools), and `core` (config, DB connections, LangSmith setup).
2.  **Configuration Management:** Use `pydantic-settings` to manage environment variables (OpenAI keys, DB credentials, LangSmith tags).
3.  **Agentic Approach:** Since the system needs to decide *when* to use a specific tool (e.g., when to query the RAG DB vs. when to write Python code to generate a chart), we will use a **Tool Calling Agent** (LangChain's `create_tool_calling_agent` paired with an Agent Executor). We will use a central Agent router that has access to the skills defined in a `skills.md` file.
4.  **Extensibility:** I will add more tools in the future. The architecture must allow me to register a new LangChain `@tool` and plug it into the Agent Executor with minimal friction.
5.  **Type Hinting:** Use strict Python type hinting everywhere. Use Pydantic models for all FastAPI request/response payloads.

# Initial Project Scope (The Modules)
The system will eventually comprise these tools, which the core Agent will have access to:
*   **Tool 1: Excel Screener:** Reads a CSV of abstracts, evaluates against criteria, and writes an accepted/rejected `.xlsx` file.
*   **Tool 2: Document Ingestor:** Parses local PDFs, chunks them, and embeds them into the PostgreSQL/pgvector database.
*   **Tool 3: Paper Planner & Title Suggester:** Queries the DB to suggest titles and generate hierarchical outlines.
*   **Tool 4: RAG Drafter:** Drafts sections based on the outline, appending specified citation styles (IEEE, APA, Vancouver).
*   **Tool 5: Analytics Sandbox:** Writes and executes Python code locally to analyze the scraped data and generate charts (`.png` files) or answer analytical questions.

# Your First Task
Acknowledge that you understand these requirements. Then, provide the following to kick off the project:
1.  The ideal standard project directory structure for this FastAPI/LangChain backend.
2.  The initial `docker-compose.yml` file to spin up the PostgreSQL/pgvector database and the FastAPI application.
3.  The `requirements.txt` (or `pyproject.toml`) with the necessary dependencies.

Do not write the application logic yet. Let's set up the infrastructure and architecture first.