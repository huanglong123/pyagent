"""
pyagent-ai: Unified LLM provider abstraction via LangChain.

Mirrors pi-mono's packages/ai — provides a single interface for creating
and using LLM models across multiple providers (OpenAI, Anthropic, Google).
"""

from pyagent_ai.providers import (
    ProviderType,
    ProviderConfig,
    get_llm,
    get_chat_model,
)
from pyagent_ai.models import MODEL_REGISTRY, get_model_info
from pyagent_ai.streaming import StreamChunk, StreamHandler
from pyagent_ai.env import load_env
from pyagent_ai.logging_config import setup_error_logging
from pyagent_ai.tracing import (
    TracingConfig,
    TraceMetadata,
    init_tracing,
    get_config,
    get_langsmith_client,
    create_dataset,
    get_project_runs,
    traceable,
    trace_context,
    measure_latency,
)

__all__ = [
    "ProviderType",
    "ProviderConfig",
    "get_llm",
    "get_chat_model",
    "MODEL_REGISTRY",
    "get_model_info",
    "StreamChunk",
    "StreamHandler",
    "load_env",
    "setup_error_logging",
    "TracingConfig",
    "TraceMetadata",
    "init_tracing",
    "get_config",
    "get_langsmith_client",
    "create_dataset",
    "get_project_runs",
    "traceable",
    "trace_context",
    "measure_latency",
]
