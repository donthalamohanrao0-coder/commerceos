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
    # Vercel gives every deployment its own *.vercel.app host; allow them all by
    # default so preview + production URLs work without re-listing each one.
    cors_allow_origin_regex: str | None = r"https://.*\.vercel\.app"

    # Frontend / demo wiring. A first-time authenticated user is auto-linked to
    # this merchant (see IdentityService); production replaces this with onboarding.
    demo_merchant_code: str = "mrc_novatech_001"

    # OpenAI — credential-gated (Phase 6). Absent in local dev; FakeOpenAIClient used until set.
    openai_api_key: str | None = None
    openai_reasoning_model: str = "gpt-5"
    openai_fast_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Razorpay — credential-gated (Phase 7). FakeRazorpayClient used until set.
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    # Pinecone — credential-gated (Phase 8). cloud/region are needed to create the
    # index if it does not exist yet (serverless spec).
    pinecone_api_key: str | None = None
    pinecone_index_name: str | None = None
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # RAG chunking + retrieval knobs (Phase 8). Pinned here, not scattered in code,
    # so the strategy can be tuned without touching the pipeline (plan.md #7).
    rag_chunk_target_tokens: int = 512
    rag_chunk_max_tokens: int = 800
    rag_chunk_overlap_tokens: int = 64
    rag_retrieval_top_k: int = 6
    rag_embedding_dimension: int = 1536  # text-embedding-3-small

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
