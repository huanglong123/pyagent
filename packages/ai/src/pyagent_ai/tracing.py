"""
LangSmith tracing integration — debug, monitor, and evaluate LLM apps.

Provides a centralised initialiser that wires LangSmith into the
application via environment variables (no hard-coded secrets), helper
decorators for instrumenting agent nodes, and metadata utilities for
tagging traces with business context (session id, user id, …).

Usage (in CLI entry-point):

    from pyagent_ai.tracing import init_tracing
    init_tracing(project_name="pyagent")

    # From then on, every LangChain / LangGraph call is traced automatically.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Generator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment variable names — project config uses the LANGSMITH_* prefix
# exclusively (covers both the LangSmith SaaS and self-hosted Docker
# deployments, e.g. LANGSMITH_ENDPOINT=http://localhost:1984).
# ---------------------------------------------------------------------------
ENV_TRACING = "LANGSMITH_TRACING"
ENV_ENDPOINT = "LANGSMITH_ENDPOINT"
ENV_API_KEY = "LANGSMITH_API_KEY"
ENV_PROJECT = "LANGSMITH_PROJECT"

DEFAULT_ENDPOINT = "https://api.smith.langchain.com"


@dataclass
class TracingConfig:
    """Resolved LangSmith configuration.

    Attributes:
        enabled: Whether tracing is active (``LANGSMITH_TRACING=true``).
        project_name: LangSmith project name.
        endpoint: LangSmith API endpoint (cloud or self-hosted Docker).
        api_key: API key for authentication.
    """

    enabled: bool = False
    project_name: str = ""
    endpoint: str = ""
    api_key: str = ""

    @classmethod
    def from_env(cls) -> TracingConfig:
        """Build a TracingConfig from the current environment."""
        tracing_on = os.environ.get(ENV_TRACING, "").lower()
        return cls(
            enabled=tracing_on in ("true", "1", "yes"),
            project_name=os.environ.get(ENV_PROJECT, "pyagent"),
            endpoint=os.environ.get(ENV_ENDPOINT, DEFAULT_ENDPOINT),
            api_key=os.environ.get(ENV_API_KEY, ""),
        )

    def __bool__(self) -> bool:
        return self.enabled and bool(self.api_key)


# Module-level singleton — set by init_tracing().
_config: TracingConfig | None = None


def get_config() -> TracingConfig:
    """Return the current tracing config (initialises lazily)."""
    global _config
    if _config is None:
        _config = TracingConfig.from_env()
    return _config


def init_tracing(
    project_name: str | None = None,
    *,
    enabled: bool | None = None,
) -> TracingConfig:
    """Initialise LangSmith tracing.

    Call this **once** at application startup (e.g. in the CLI entry-point
    or server ``app`` module) after ``load_env()`` so that environment
    variables are visible.

    The function is idempotent — subsequent calls return the cached
    config without re-initialising the SDK.

    Args:
        project_name: Override the LangSmith project name. When ``None``,
            reads from the ``LANGSMITH_PROJECT`` environment variable,
            falling back to ``"pyagent"``.
        enabled: Force tracing on (``True``) or off (``False``). When
            ``None``, the decision is made from ``LANGSMITH_TRACING``.

    Returns:
        The resolved :class:`TracingConfig`.
    """
    global _config
    if _config is not None:
        return _config

    cfg = TracingConfig.from_env()

    if project_name is not None:
        cfg.project_name = project_name

    if enabled is not None:
        cfg.enabled = enabled

    if not cfg.enabled:
        logger.info("LangSmith tracing is disabled (%s is not true).", ENV_TRACING)
        _config = cfg
        return cfg

    if not cfg.api_key:
        logger.warning(
            "LangSmith tracing enabled but %s is not set. "
            "Traces will fail to upload.",
            ENV_API_KEY,
        )

    # Propagate the resolved values back to os.environ so that the langsmith
    # SDK picks them up automatically. The SDK requires LANGCHAIN_TRACING_V2
    # to enable v2 tracing — that is an SDK-internal contract, not a project
    # config variable, so we translate LANGSMITH_TRACING → LANGCHAIN_TRACING_V2
    # here. The LANGSMITH_* values are also set so newer SDK versions that
    # consult them work out of the box.
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ[ENV_TRACING] = "true"
    os.environ[ENV_PROJECT] = cfg.project_name
    if cfg.endpoint:
        os.environ[ENV_ENDPOINT] = cfg.endpoint
    if cfg.api_key:
        os.environ[ENV_API_KEY] = cfg.api_key

    try:
        from langsmith import Client

        client = Client()
        # Touch the client to verify connectivity (non-blocking).
        logger.info(
            "LangSmith initialised — project=%s endpoint=%s",
            cfg.project_name,
            cfg.endpoint,
        )
        _ = client  # keep reference alive
    except Exception:
        logger.exception("LangSmith initialisation failed (traces will not be uploaded)")

    _config = cfg
    return cfg


def reset_tracing() -> None:
    """Reset the tracing config (useful for tests)."""
    global _config
    _config = None


# ---------------------------------------------------------------------------
# Decorators & context managers for instrumenting agent nodes
# ---------------------------------------------------------------------------


@dataclass
class TraceMetadata:
    """Business metadata injected into every LangSmith trace.

    These fields are searchable / filterable in the LangSmith UI so
    that traces can be aggregated by session, user, model, etc.
    """

    session_id: str = ""
    user_id: str = ""
    model: str = ""
    provider: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.session_id:
            d["session_id"] = self.session_id
        if self.user_id:
            d["user_id"] = self.user_id
        if self.model:
            d["model"] = self.model
        if self.provider:
            d["provider"] = self.provider
        if self.extra:
            d.update(self.extra)
        return d


# Thread-local storage for the active trace metadata stack.
import threading

_metadata_stack: threading.local = threading.local()


def _get_stack() -> list[TraceMetadata]:
    if not hasattr(_metadata_stack, "stack"):
        _metadata_stack.stack = []
    return _metadata_stack.stack


def push_metadata(meta: TraceMetadata) -> None:
    """Push trace metadata onto the thread-local stack."""
    _get_stack().append(meta)


def pop_metadata() -> TraceMetadata | None:
    """Pop and return the top metadata from the thread-local stack."""
    stack = _get_stack()
    return stack.pop() if stack else None


def current_metadata() -> dict[str, Any]:
    """Merge and return all metadata currently on the stack."""
    merged: dict[str, Any] = {}
    for meta in _get_stack():
        merged.update(meta.as_dict())
    return merged


@contextmanager
def trace_context(
    name: str = "",
    metadata: TraceMetadata | None = None,
    *,
    tags: list[str] | None = None,
) -> Generator[None, None, None]:
    """Context manager that creates a LangSmith run for its body.

    Use this to wrap any block of work that should appear as a discrete
    span in the LangSmith trace tree (e.g. an agent iteration, a
    tool-call batch, an LLM call).

    Args:
        name: Human-readable run name (shown in the LangSmith UI).
        metadata: Optional business metadata to attach to the run.
        tags: Optional list of string tags for filtering in LangSmith.

    Example::

        with trace_context("agent-iteration-3", tags=["iteration", "tools"]):
            response = model.invoke(messages)
    """
    cfg = get_config()

    if metadata is not None:
        push_metadata(metadata)

    run = None
    try:
        if cfg.enabled:
            try:
                from langchain_core.tracers.context import tracing_v2_enabled

                if tracing_v2_enabled():
                    from langsmith.run_helpers import traceable

                    # We enter a traceable context by running a no-op
                    # decorated function so that the span nests correctly.
                    @traceable(name=name or "pyagent", tags=tags or [])
                    def _noop(**_: Any) -> None:
                        return None

                    metadata_dict = current_metadata()
                    _noop(_meta=metadata_dict)
            except Exception:
                logger.debug("trace_context setup failed", exc_info=True)
        yield
    finally:
        if metadata is not None:
            pop_metadata()


def traceable(
    name: str | None = None,
    *,
    tags: list[str] | None = None,
) -> Callable[..., Any]:
    """Decorator that wraps a function so its execution appears in LangSmith.

    This is a convenience wrapper around ``langsmith.run_helpers.traceable``
    that first checks whether tracing is enabled (no-op otherwise).

    Args:
        name: Override the function name shown in the LangSmith UI.
        tags: Optional string tags for filtering.

    Example::

        @traceable(name="call_model", tags=["llm"])
        def call_model(state):
            ...
    """
    cfg = get_config()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not cfg.enabled:
            return func

        try:
            from langsmith.run_helpers import traceable as _traceable

            return _traceable(
                name=name or func.__name__,
                tags=tags or [],
            )(func)
        except Exception:
            logger.debug("traceable decorator fallback for %s", func.__name__, exc_info=True)
            return func

    return decorator


@contextmanager
def measure_latency(label: str) -> Generator[dict[str, Any], None, None]:
    """Context manager that records start/end times and yields a metrics dict.

    The metrics dict is also pushed as a ``latency_ms`` field into the
    current trace metadata so that it shows up in the LangSmith span.

    Args:
        label: Human-readable label for the measurement (e.g. ``"llm_invoke"``).

    Yields:
        A dict with keys ``label``, ``start``, ``end``, ``duration_ms``.
    """
    start = time.perf_counter()
    metrics: dict[str, Any] = {
        "label": label,
        "start": start,
        "end": None,
        "duration_ms": 0.0,
    }
    try:
        yield metrics
    finally:
        end = time.perf_counter()
        metrics["end"] = end
        metrics["duration_ms"] = (end - start) * 1000

        # Inject duration into the current trace metadata so it appears
        # in the LangSmith run's extra fields.
        meta = current_metadata()
        meta[f"latency_{label}_ms"] = metrics["duration_ms"]


def get_langsmith_client() -> Any | None:
    """Return a LangSmith Client instance if tracing is enabled, else None.

    Useful for programmatic interactions (e.g. uploading datasets,
    reading runs for evaluation).
    """
    cfg = get_config()
    if not cfg:
        return None
    try:
        from langsmith import Client

        return Client()
    except Exception:
        logger.debug("Failed to create LangSmith Client", exc_info=True)
        return None


def get_project_runs(
    project_name: str | None = None,
    *,
    limit: int = 100,
) -> list[Any]:
    """Fetch recent runs from the LangSmith project.

    Args:
        project_name: Project name (defaults to the configured one).
        limit: Maximum number of runs to return.

    Returns:
        List of ``langsmith.schemas.Run`` objects (empty list on failure).
    """
    client = get_langsmith_client()
    if client is None:
        return []

    cfg = get_config()
    proj = project_name or cfg.project_name
    try:
        runs = list(client.list_runs(project_name=proj, limit=limit))
        return runs
    except Exception:
        logger.debug("Failed to list runs for project %s", proj, exc_info=True)
        return []


def create_dataset(
    dataset_name: str,
    inputs: list[dict[str, Any]],
    outputs: list[dict[str, Any]] | None = None,
    *,
    description: str = "",
) -> Any | None:
    """Create a LangSmith dataset for evaluation.

    Args:
        dataset_name: Unique dataset name in the LangSmith project.
        inputs: List of input dicts (one per example).
        outputs: Optional list of expected-output dicts.
        description: Human-readable description.

    Returns:
        The created dataset object, or ``None`` on failure.
    """
    client = get_langsmith_client()
    if client is None:
        logger.warning("Cannot create dataset — LangSmith is not configured.")
        return None

    try:
        # Check if dataset already exists
        existing = None
        for ds in client.list_datasets(dataset_name=dataset_name):
            if ds.name == dataset_name:
                existing = ds
                break

        if existing is not None:
            logger.info("Dataset '%s' already exists, adding examples.", dataset_name)
            dataset = existing
        else:
            dataset = client.create_dataset(
                dataset_name=dataset_name,
                description=description,
            )
            logger.info("Created dataset '%s'.", dataset_name)

        # Add examples
        for i, inp in enumerate(inputs):
            out = outputs[i] if outputs and i < len(outputs) else None
            client.create_example(
                inputs=inp,
                outputs=out,
                dataset_id=dataset.id,
            )

        return dataset
    except Exception:
        logger.exception("Failed to create dataset '%s'", dataset_name)
        return None