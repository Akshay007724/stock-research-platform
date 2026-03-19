"""
Shared LLM client factory.

Supports two providers via a single config flag (LLM_PROVIDER):
  - "groq"   → Llama-3.3-70B on Groq (free, fast, strong reasoning) [default]
  - "openai" → OpenAI GPT models (requires OPENAI_API_KEY)

Both use the openai SDK — Groq exposes an OpenAI-compatible REST API so no
extra package is needed.

Model capability comparison for financial reasoning tasks:
  llama-3.3-70b-versatile  ≈ GPT-4o in quality, much faster than gpt-4o-mini
  gpt-4o-mini              ≈ decent but weaker multi-step reasoning
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def get_client() -> AsyncOpenAI | None:
    """Return a configured AsyncOpenAI client for the active LLM provider."""
    provider = settings.llm_provider.lower()

    if provider == "groq":
        if not settings.groq_api_key:
            logger.warning("LLM_PROVIDER=groq but GROQ_API_KEY is not set — falling back to OpenAI")
        else:
            return AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url=_GROQ_BASE_URL,
            )

    # Fallback to OpenAI
    if settings.openai_api_key:
        return AsyncOpenAI(api_key=settings.openai_api_key)

    logger.warning("No LLM API key configured (GROQ_API_KEY or OPENAI_API_KEY) — agent reasoning will use fallback logic")
    return None


def get_model() -> str:
    """Return the model name for the active provider."""
    provider = settings.llm_provider.lower()
    if provider == "groq" and settings.groq_api_key:
        return settings.groq_model      # llama-3.3-70b-versatile
    return settings.openai_model        # gpt-4o-mini


def provider_label() -> str:
    """Human-readable label for log messages."""
    provider = settings.llm_provider.lower()
    if provider == "groq" and settings.groq_api_key:
        return f"Groq/{settings.groq_model}"
    return f"OpenAI/{settings.openai_model}"
