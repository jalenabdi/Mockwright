"""Application settings, read once from the environment.

`.env` at the repository root is loaded here, so every module that needs a
setting imports it from this file instead of calling os.environ directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

# Local SQLite file by default; set DATABASE_URL to use Postgres instead.
PLACEHOLDER_SECRETS = {"change-me", "your_jwt_secret"}

DEFAULT_DATABASE_URL = f"sqlite:///{(REPO_ROOT / 'mockwright.db').as_posix()}"


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}.") from exc


def normalize_database_url(url: str) -> str:
    """Point plain postgres URLs at the psycopg 3 driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    access_token_expire_minutes: int
    gemini_api_key: str
    gemini_model: str
    deepgram_api_key: str
    deepgram_stt_model: str
    deepgram_tts_model: str
    cors_origins: list[str] = field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    secret_key = os.environ.get("SECRET_KEY", "").strip()
    if not secret_key or secret_key in PLACEHOLDER_SECRETS:
        raise RuntimeError(
            "SECRET_KEY is missing or still the placeholder. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        database_url=normalize_database_url(
            os.environ.get("DATABASE_URL", "").strip() or DEFAULT_DATABASE_URL
        ),
        secret_key=secret_key,
        access_token_expire_minutes=_int("ACCESS_TOKEN_EXPIRE_MINUTES", 1440),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite").strip(),
        deepgram_api_key=os.environ.get("DEEPGRAM_API_KEY", "").strip(),
        deepgram_stt_model=os.environ.get("DEEPGRAM_STT_MODEL", "nova-3").strip(),
        deepgram_tts_model=os.environ.get("DEEPGRAM_TTS_MODEL", "aura-2-thalia-en").strip(),
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
    )
