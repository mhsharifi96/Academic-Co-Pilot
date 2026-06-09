from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.4-mini"

    # PostgreSQL / pgvector Configuration
    DATABASE_URL: str

    # Crossref "polite pool" contact email. Not a secret and not required, but
    # identifying your traffic gets better/more predictable rate limits.
    CROSSREF_MAILTO: str = "paperagent@example.com"

    # Elsevier (Scopus) Search API key. Secret — set via .env, never commit.
    # Optional: the Scopus search tool reports a friendly message when unset.
    ELSEVIER_API_KEY: Optional[str] = None

    # Authentication (JWT)
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Human-in-the-loop: when True, sensitive tools (code execution, drafting,
    # ingestion) pause for explicit approve/edit/reject before running. When
    # False (default), the agent executes its whole plan autonomously and only
    # returns the final result. Set REQUIRE_TOOL_APPROVAL=true in .env to gate.
    REQUIRE_TOOL_APPROVAL: bool = False

    # LangSmith Configuration
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "paper-agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
