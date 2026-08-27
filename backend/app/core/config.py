from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    app_name: str = "CommerceOS API"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://commerceos:commerceos@localhost:5432/commerceos"

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    # OpenAI — credential-gated (Phase 6). Absent in local dev; FakeOpenAIClient used until set.
    openai_api_key: str | None = None
    openai_reasoning_model: str = "gpt-5"
    openai_fast_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Razorpay — credential-gated (Phase 7). FakeRazorpayClient used until set.
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    # Pinecone — credential-gated (Phase 8).
    pinecone_api_key: str | None = None
    pinecone_index: str | None = None

    # Supabase — credential-gated cutover. Local Postgres used until set.
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_anon_key: str | None = None

    # Observability — instrumentation always wired; each no-ops until its key/DSN is set.
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    sentry_dsn: str | None = None
    otel_exporter_otlp_endpoint: str | None = None

    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
