"""
config.py — Application Configuration
--------------------------------------
Pydantic BaseSettings reads values from your .env file automatically.
No more hardcoded secrets. No more "oops I pushed my API key to GitHub."

HOW IT WORKS:
  1. You put secrets in .env (which is gitignored)
  2. Pydantic reads .env at startup
  3. Your code accesses settings.GEMINI_API_KEY — clean and safe

CONCEPT: Pydantic validates the types too! If you put DEBUG="yes" in .env
         and the field is `DEBUG: bool`, Pydantic converts "yes" → True.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Smart Document Hub"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-before-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ─────────────────────────────────────────────────────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "smart_document_hub"

    # ── AI / LLM ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""

    # ── Vector DB ────────────────────────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # ── Background Tasks ─────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── File Storage ─────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── Translation ──────────────────────────────────────────────────────────
    TRANSLATOR: str = "google"

    # Pydantic v2 way: tell it to load from .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# lru_cache means this function runs ONCE and the result is cached.
# Every time code calls get_settings(), it gets the SAME Settings object.
# This is the standard pattern — you don't want to re-read .env 1000 times.
@lru_cache
def get_settings() -> Settings:
    return Settings()


# Convenient shortcut: from app.config import settings
settings = get_settings()
