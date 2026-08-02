"""
LLM provider configuration and factory.

Provides a unified interface for creating LangChain chat models across
multiple providers. This mirrors pi-mono's provider abstraction in
packages/ai, where a single ProviderConfig selects the backend and
returns a model instance with streaming support.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider.

    Attributes:
        provider: Which provider backend to use.
        model: Model name (e.g. "gpt-4o-mini", "claude-3-5-sonnet").
        temperature: Sampling temperature (0.0 - 2.0).
        max_tokens: Maximum output tokens.
        api_key: API key. If None, reads from environment.
        base_url: Custom base URL for OpenAI-compatible providers.
        streaming: Whether to enable streaming.
    """

    provider: ProviderType = ProviderType.OPENAI
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int | None = None
    api_key: str | None = None
    base_url: str | None = None
    streaming: bool = True

    def resolve_api_key(self) -> str | None:
        """Resolve the API key from config or environment."""
        if self.api_key:
            return self.api_key
        env_map = {
            ProviderType.OPENAI: "OPENAI_API_KEY",
            ProviderType.ANTHROPIC: "ANTHROPIC_API_KEY",
            ProviderType.GOOGLE: "GOOGLE_API_KEY",
            ProviderType.OPENAI_COMPATIBLE: "OPENAI_API_KEY",
            ProviderType.OLLAMA: None,
        }
        env_var = env_map.get(self.provider)
        if env_var:
            return os.environ.get(env_var)
        return None


def get_chat_model(config: ProviderConfig | None = None) -> Any:
    """Create a LangChain chat model from a ProviderConfig.

    This is the primary entry point for obtaining an LLM instance.
    The returned object supports .invoke() and .stream() as per
    LangChain's BaseChatModel interface.

    Args:
        config: Provider configuration. If None, reads defaults from
                environment variables.

    Returns:
        A LangChain BaseChatModel instance.
    """
    if config is None:
        config = ProviderConfig(
            provider=ProviderType(os.environ.get("PYAGENT_MODEL_PROVIDER", "openai")),
            model=os.environ.get("PYAGENT_MODEL_NAME", "gpt-4o-mini"),
            temperature=float(os.environ.get("PYAGENT_MODEL_TEMPERATURE", "0.7")),
        )

    api_key = config.resolve_api_key()
    common_kwargs: dict[str, Any] = {
        "temperature": config.temperature,
    }
    if config.max_tokens is not None:
        common_kwargs["max_tokens"] = config.max_tokens

    if config.provider == ProviderType.OPENAI:
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": config.model,
            "api_key": api_key,
            "streaming": config.streaming,
            **common_kwargs,
        }
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenAI(**kwargs)

    elif config.provider == ProviderType.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=config.model,
            api_key=api_key,
            streaming=config.streaming,
            **common_kwargs,
        )

    elif config.provider == ProviderType.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=api_key,
            **common_kwargs,
        )

    elif config.provider == ProviderType.OLLAMA:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=config.model,
            base_url=config.base_url or "http://localhost:11434",
            **common_kwargs,
        )

    elif config.provider == ProviderType.OPENAI_COMPATIBLE:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model,
            api_key=api_key or "dummy",
            base_url=config.base_url or "http://localhost:8000/v1",
            streaming=config.streaming,
            **common_kwargs,
        )

    else:
        raise ValueError(f"Unknown provider: {config.provider}")


def get_llm(config: ProviderConfig | None = None) -> Any:
    """Alias for get_chat_model — kept for API parity with pi-mono."""
    return get_chat_model(config)
