"""
Application configuration.
All settings are loaded from environment variables (via .env file).
Never hard-code secrets here.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "Enterprise Multi-Agent AI Intelligence Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = "talentgraph_super_secret_development_key_2026"

    # ── LLM ──────────────────────────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_PROVIDER: str = "azure"            # azure | google | openai | anthropic

    # ── Azure OpenAI ──────────────────────────────────────────────────────────
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"

    # ── External Search ───────────────────────────────────────────────────────
    SEARCH_API_KEY: str = ""
    SEARCH_ENGINE_ID: str = ""

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # ── File Upload ───────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10            # per file

    # ── Vector Store ──────────────────────────────────────────────────────────
    VECTOR_STORE_DIR: str = "data/vector_store"

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (safe to call many times)."""
    return Settings()
