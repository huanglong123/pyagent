"""
Model registry — known model configurations across providers.

Maps model names to their metadata (context window, provider, description).
This mirrors pi-mono's packages/ai/src/models.generated.ts which tracks
model capabilities for routing and display.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Metadata for a single LLM model."""

    name: str
    provider: str
    context_window: int = 4096
    supports_tools: bool = True
    supports_streaming: bool = True
    description: str = ""


MODEL_REGISTRY: dict[str, ModelInfo] = {
    # OpenAI
    "gpt-4o": ModelInfo(
        name="gpt-4o",
        provider="openai",
        context_window=128000,
        description="OpenAI GPT-4o multimodal model",
    ),
    "gpt-4o-mini": ModelInfo(
        name="gpt-4o-mini",
        provider="openai",
        context_window=128000,
        description="OpenAI GPT-4o-mini - cost-effective",
    ),
    "gpt-4-turbo": ModelInfo(
        name="gpt-4-turbo",
        provider="openai",
        context_window=128000,
        description="OpenAI GPT-4 Turbo",
    ),
    "o1": ModelInfo(
        name="o1",
        provider="openai",
        context_window=200000,
        supports_streaming=False,
        description="OpenAI o1 reasoning model",
    ),
    "o1-mini": ModelInfo(
        name="o1-mini",
        provider="openai",
        context_window=128000,
        supports_streaming=False,
        description="OpenAI o1-mini reasoning model",
    ),
    # Anthropic
    "claude-3-5-sonnet-20241022": ModelInfo(
        name="claude-3-5-sonnet-20241022",
        provider="anthropic",
        context_window=200000,
        description="Anthropic Claude 3.5 Sonnet",
    ),
    "claude-3-5-haiku-20241022": ModelInfo(
        name="claude-3-5-haiku-20241022",
        provider="anthropic",
        context_window=200000,
        description="Anthropic Claude 3.5 Haiku - fast",
    ),
    "claude-3-opus-20240229": ModelInfo(
        name="claude-3-opus-20240229",
        provider="anthropic",
        context_window=200000,
        description="Anthropic Claude 3 Opus - most capable",
    ),
    # Google
    "gemini-2.0-flash": ModelInfo(
        name="gemini-2.0-flash",
        provider="google",
        context_window=1000000,
        description="Google Gemini 2.0 Flash",
    ),
    "gemini-1.5-pro": ModelInfo(
        name="gemini-1.5-pro",
        provider="google",
        context_window=2000000,
        description="Google Gemini 1.5 Pro - large context",
    ),
    # Ollama (local)
    "llama3.2": ModelInfo(
        name="llama3.2",
        provider="ollama",
        context_window=128000,
        description="Llama 3.2 via Ollama (local)",
    ),
    "qwen2.5": ModelInfo(
        name="qwen2.5",
        provider="ollama",
        context_window=32768,
        description="Qwen 2.5 via Ollama (local)",
    ),
}


def get_model_info(name: str) -> ModelInfo | None:
    """Look up model info by name. Returns None if not found."""
    return MODEL_REGISTRY.get(name)


def list_models(provider: str | None = None) -> list[ModelInfo]:
    """List all known models, optionally filtered by provider."""
    models = list(MODEL_REGISTRY.values())
    if provider:
        models = [m for m in models if m.provider == provider]
    return models
