"""Shared Gemini client.

One cached google-genai client for both question generation and feedback.
"""
from __future__ import annotations

from functools import lru_cache

from google import genai
from google.genai import types

from ..config import get_settings

REQUEST_TIMEOUT_MS = 15_000

# Gemini often returns 503 (high demand) or 504 (deadline) for a moment, then
# recovers. One quick retry rides that out before callers fall back.
RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=2,
    initial_delay=0.5,
    max_delay=2.0,
    http_status_codes=[429, 500, 503, 504],
)


class GeminiUnavailableError(RuntimeError):
    """GEMINI_API_KEY is not configured."""


@lru_cache
def get_gemini_client() -> genai.Client:
    api_key = get_settings().gemini_api_key
    if not api_key:
        raise GeminiUnavailableError("GEMINI_API_KEY is not set.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS, retry_options=RETRY_OPTIONS),
    )
