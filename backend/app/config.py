"""
config.py — Application configuration, loaded from environment / .env via pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Smart Document Hub"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-before-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    # ── Database ─────────────────────────────────────────────────────────────
    # Set MONGODB_URL="mock://" to run fully in-memory (no MongoDB needed).
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "smart_document_hub"
    # If the real MongoDB is unreachable at startup, fall back to an in-memory DB.
    MONGODB_FALLBACK_TO_MOCK: bool = True

    # ── AI / LLM ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── Vector DB ────────────────────────────────────────────────────────────
    CHROMA_PATH: str = "./chroma_data"
    # all-MiniLM puts unrelated official documents around 0.35–0.45; 0.5+ is a real topical link.
    GRAPH_SIMILARITY_THRESHOLD: float = 0.50

    # ── Cache / rate limiting ────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── File Storage ─────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Translation ──────────────────────────────────────────────────────────
    TRANSLATOR: str = "google"  # google | gemini | none

    # ── Demo ─────────────────────────────────────────────────────────────────
    # Seeds a demo account + sample documents on startup when the DB is empty.
    SEED_DEMO: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
