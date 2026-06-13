from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Deployment environment: "development" (default) or "production". Use this
    # to gate environment-specific behavior (stricter defaults, disabled debug,
    # etc.). Set ENVIRONMENT=production in .env for production deployments.
    ENVIRONMENT: str = "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-5.4-nano"
    # A stronger model for high-stakes tools (reference checking, humanizing) that
    # need better reasoning than the agents' cheap everyday model. Routed via the
    # "powerful" tier in app/repositories/llm.py.
    POWERFUL_MODEL: str = "gpt-5.4-mini"
    # Image model used by the LLM repository's generate_image() (infographics).
    IMAGE_MODEL: str = "gpt-image-1"

    # PostgreSQL / pgvector Configuration
    DATABASE_URL: str

    # Crossref "polite pool" contact email. Not a secret and not required, but
    # identifying your traffic gets better/more predictable rate limits.
    CROSSREF_MAILTO: str = "paperagent@example.com"

    # Elsevier (Scopus) Search API key. Secret — set via .env, never commit.
    # Optional: the Scopus search tool reports a friendly message when unset.
    ELSEVIER_API_KEY: Optional[str] = None

    # OpenAlex API key. Since 2026-02-13 OpenAlex requires a key for real use
    # (usage-based credits; a free key grants $1/day). A few unauthenticated
    # calls still work for testing, then return HTTP 409. Optional here: the
    # tool runs keyless for light use and reports a friendly message when it
    # hits the limit. Get a free key at https://openalex.org/settings/api-key
    OPENALEX_API_KEY: Optional[str] = None

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
