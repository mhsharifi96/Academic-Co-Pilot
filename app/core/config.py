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

    # ---- Provider PDF download queue ---------------------------------------
    # External provider that serves full-text PDFs by DOI. The token is a
    # BACKEND SECRET — it is only ever used server-side in the download worker
    # and must never be sent to the frontend. Leave PROVIDER_TOKEN unset to run
    # without downloads (jobs will fail with a provider error).
    PROVIDER_BASE_URL: str = "http://provide.falinoos.ir:8081"
    PROVIDER_TOKEN: Optional[str] = None
    PROVIDER_TIMEOUT: float = 60.0
    # Per-user quota: at most DOWNLOAD_QUOTA_LIMIT originating requests per
    # rolling DOWNLOAD_QUOTA_WINDOW_HOURS. Retries reuse the same job row and do
    # NOT consume additional quota.
    DOWNLOAD_QUOTA_LIMIT: int = 10
    DOWNLOAD_QUOTA_WINDOW_HOURS: int = 24
    # Retry policy: at most DOWNLOAD_MAX_ATTEMPTS attempts; on a 404 the job is
    # rescheduled with a future available_at (worker never sleeps for the delay).
    # DOWNLOAD_RETRY_DELAYS_MIN lists the minutes before attempt 2, attempt 3, …
    DOWNLOAD_MAX_ATTEMPTS: int = 3
    DOWNLOAD_RETRY_DELAYS_MIN: str = "10,20"
    # First three requests are FAST (target ~1h); requests 4..10 are STANDARD,
    # spread across the next 24h at these hour offsets (index = request_number-4).
    FAST_TARGET_MINUTES: int = 60
    STANDARD_TARGET_HOURS: int = 24
    STANDARD_OFFSETS_HOURS: str = "1,5,9,12,16,20,24"
    # Deterministic per-user jitter (± minutes) so different users' scheduled
    # jobs don't all become available at exactly the same instant.
    SCHEDULE_JITTER_MINUTES: int = 15
    # Anti-starvation: after this many FAST jobs, serve one eligible STANDARD job.
    FAST_BEFORE_STANDARD: int = 5
    # A FAST job whose target_deadline is within this many minutes jumps the queue.
    DEADLINE_URGENT_MINUTES: int = 10
    # Background worker poll interval when the queue has no eligible job.
    WORKER_POLL_SECONDS: float = 5.0
    # Start the background download worker on app startup. Disabled in tests.
    ENABLE_DOWNLOAD_WORKER: bool = True

    # LangSmith Configuration
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_ENDPOINT: Optional[str] = None
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "paper-agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
