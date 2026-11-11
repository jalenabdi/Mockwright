"""Shared Gemini client.

One cached google-genai client for both question generation and feedback.
"""
from __future__ import annotations

from functools import lru_cache

from google import genai
from google.genai import types

from ..config import get_settings

REQUEST_TIMEOUT_MS = 30_000


class GeminiUnavailableError(RuntimeError):
    """GEMINI_API_KEY is not configured."""


@lru_cache
def get_gemini_client() -> genai.Client:
    api_key = get_settings().gemini_api_key
    if not api_key:
        raise GeminiUnavailableError("GEMINI_API_KEY is not set.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
