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

    # When set, the user who registers with this email is automatically granted
    # admin on startup (idempotent), so a production deployment has a guaranteed
    # admin regardless of registration order. The account must still register
    # normally first; this only flips its is_admin flag. Leave unset to rely on
    # the "first account to register becomes admin" fallback in auth.register.
    ADMIN_EMAIL: Optional[str] = None

    # Authentication (JWT)
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Human-in-the-loop: when True, sensitive tools (code execution, drafting,
    # ingestion) pause for explicit approve/edit/reject before running. When
    # False (default), the agent executes its whole plan autonomously and only
    # returns the final result. Set REQUIRE_TOOL_APPROVAL=true in .env to gate.
    REQUIRE_TOOL_APPROVAL: bool = False

    # ---- Per-user balance / usage billing ----------------------------------
    # When True, every chat turn deducts its measured token cost from the
    # user's balance, and a user whose balance is exhausted is blocked from
    # chatting until an admin tops them up. Set ENABLE_BILLING=false to disable
    # metering entirely (useful for local development / the test suite).
    ENABLE_BILLING: bool = True
    # Dollars granted to a brand-new account.
    DEFAULT_USER_BALANCE: float = 0.5
    # A user is blocked from starting a new turn once balance <= this value.
    MIN_BALANCE_TO_CHAT: float = 0.0
    # Token prices in USD per 1,000,000 tokens, used to convert measured token
    # usage into a dollar cost. Defaults are sensible for the cheap "nano" tier;
    # override per deployment to match the actual model pricing.
    COST_INPUT_PER_1M: float = 0.15
    COST_OUTPUT_PER_1M: float = 0.60

    # ---- Agent guardrails ---------------------------------------------------
    # When True, each incoming user message is screened (fast keyword rules +
    # an LLM classifier) before the agent runs. Off-topic requests and prompt-
    # injection / jailbreak / system-abuse attempts are refused without ever
    # reaching the agent. Set ENABLE_GUARDRAILS=false to disable.
    ENABLE_GUARDRAILS: bool = True
    # Model used by the guardrail classifier. Falls back to OPENAI_MODEL when
    # unset — keep it cheap, this runs on every message.
    GUARDRAIL_MODEL: Optional[str] = None

    # LangSmith Configuration
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "paper-agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
