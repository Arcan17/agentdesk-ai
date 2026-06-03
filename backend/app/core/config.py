"""Application settings loaded from environment (pydantic-settings).

No secret is ever hardcoded; every value is overridable via environment / .env.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- General ---
    app_name: str = "AgentDesk AI"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Database / cache ---
    database_url: str = Field(
        default="postgresql+asyncpg://agentdesk:agentdesk@localhost:5432/agentdesk"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    # --- Auth ---
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7

    # --- Providers (LLM / embeddings) ---
    llm_provider: str = "mock"  # mock | anthropic | openai
    embedding_provider: str = "mock"  # mock | anthropic | openai
    embedding_dim: int = 384
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # --- Agent workflow thresholds ---
    confidence_threshold: float = 0.7
    similarity_threshold: float = 0.5
    retrieval_top_k: int = 5
    # Run the agent workflow inline instead of dispatching to Celery (tests/local demos).
    agent_run_eager: bool = False

    # --- Webhooks ---
    webhook_max_retries: int = 5
    webhook_backoff_base_seconds: float = 2.0
    webhook_timeout_seconds: float = 10.0
    # Deliver webhooks inline instead of dispatching to Celery (local demos).
    webhook_delivery_eager: bool = False
    # When False, deliveries are still recorded but not dispatched (used in tests).
    webhook_dispatch_enabled: bool = True

    # --- Security / HTTP ---
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
