"""Application settings (pydantic-settings). No insecure defaults for secrets."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (required — no default, for security)
    DATABASE_URL: str = Field(..., description="postgresql://… (asyncpg is forced at engine build)")
    DATABASE_POOL_SIZE: int = Field(default=10)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    # Fail fast on pool exhaustion instead of stalling (carried from agent_framework's
    # AUTH_LOGIN_SESSION_RACE lessons — an unbounded checkout wait widens session-race windows).
    DATABASE_POOL_TIMEOUT: int = Field(default=30)

    REDIS_URL: str = Field(default="redis://redis:6379/0")

    # Where validation machines live (verified at boot).
    MACHINES_DIR: str = Field(default="machines")
    # Bounded worker concurrency — OCR/LLM are the heavy bit; never unbounded.
    WORKER_CONCURRENCY: int = Field(default=2)
    # When true, the API enqueues to Redis and the dedicated worker processes runs.
    # Default false → in-process BackgroundTasks (simplest demo path).
    USE_REDIS_QUEUE: bool = Field(default=False)

    # Blob storage (local volume now; an S3/Spaces adapter slots in behind storage/).
    STORAGE_DIR: str = Field(default="data/blobs")

    # Bootstrap auth: a single shared API key (multi-tenant/JWT is a later milestone).
    API_KEY: str = Field(..., description="shared bearer key for write endpoints")

    # OCR / extraction
    OCR_DPI: int = Field(default=200)
    EXTRACTOR: str = Field(default="deterministic", description="deterministic | llm")

    # LLM (Together) — powers the AI-assisted analysis + revised-document generation.
    # The structural verdict stays machine-verified; the LLM only adds the analysis/redline.
    TOGETHER_API_KEY: str = Field(default="", description="empty → analysis/revision skipped")
    TOGETHER_MODEL: str = Field(default="meta-llama/Llama-3.3-70B-Instruct-Turbo")
    TOGETHER_BASE_URL: str = Field(default="https://api.together.xyz/v1")

    @property
    def llm_enabled(self) -> bool:
        return bool(self.TOGETHER_API_KEY)

    ENVIRONMENT: str = Field(default="production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
