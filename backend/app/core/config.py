from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://enterprisegpt:enterprisegpt@localhost:5432/enterprisegpt"
    database_url_sync: str = "postgresql://enterprisegpt:enterprisegpt@localhost:5432/enterprisegpt"

    # Security
    secret_key: str = "dev-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "enterprisegpt_chunks"
    qdrant_api_key: str | None = None

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # File storage
    upload_dir: str = "./storage/uploads"
    max_upload_mb: int = 25

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 120

    # --- Phase 2: LLM / RAG ---
    # "ollama" (default, no API key / fully local), "openai", or "gemini"
    llm_provider: str = "ollama"

    # Ollama (local inference server, no API key required)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_timeout_seconds: int = 120

    # OpenAI (optional cloud fallback, only used if llm_provider="openai")
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # Gemini (optional cloud fallback, only used if llm_provider="gemini")
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    # RAG retrieval
    rag_top_k: int = 5
    rag_max_context_chars: int = 6000
    llm_temperature: float = 0.2
    llm_max_tokens: int = 800
    
    # --- Phase 4 Additions ---
    hybrid_search_enabled: bool = True

    # RAGAS needs a judge LLM to score faithfulness/relevancy/precision.
    # If unset, evaluation_service falls back to heuristic scoring automatically.
    ragas_judge_llm_api_key: str | None = None
    ragas_judge_llm_model: str = "gpt-4o-mini"

    # Multi-agent routing
    agent_routing_enabled: bool = True
    # --- Phase 5 Additions ---
    # Rate limiting (Redis-backed, shared correctly across multiple workers)
    redis_url: str = "redis://localhost:6379/0"
    # Refresh tokens
    refresh_token_expire_days: int = 14
    # Error tracking (optional -- leave unset to disable)
    sentry_dsn: str | None = None
    # App
    env: str = "development"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {".pdf", ".docx", ".txt", ".csv"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
