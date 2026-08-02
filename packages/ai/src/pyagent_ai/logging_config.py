"""
Runtime error logging configuration.

Sets up a rotating file handler that persists all runtime errors (with full
tracebacks) to an error log file, so failures can be diagnosed after the fact.
This mirrors the ``load_env()`` pattern: a once-at-startup, cross-cutting
configuration helper that the CLI and server both call before doing work.

The handler is attached to the **root logger** at ``ERROR`` level, so it
captures not only ``pyagent.*`` loggers but also errors propagated up from
third-party libraries (langchain, openai, httpx, ...). ``logger.exception(...)``
calls anywhere in the codebase therefore land in the file automatically.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Marker attribute used to recognise a handler installed by this module, so
# repeated calls to ``setup_error_logging()`` do not stack duplicate handlers.
_HANDLER_MARKER = "_pyagent_error_handler"

DEFAULT_LOG_PATH = ".pyagent/error.log"
DEFAULT_LOG_LEVEL = "ERROR"
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
DEFAULT_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _level_value(level: str | int) -> int:
    """Resolve a level given as a name (e.g. ``"ERROR"``) or numeric value."""
    if isinstance(level, int):
        return level
    resolved = logging.getLevelName(level.strip().upper())
    if not isinstance(resolved, int):
        raise ValueError(f"Invalid log level: {level!r}")
    return resolved


def _existing_handler(root_logger: logging.Logger) -> logging.Handler | None:
    """Return the pyagent error handler if already attached, else None."""
    for handler in root_logger.handlers:
        if getattr(handler, _HANDLER_MARKER, False):
            return handler
    return None


def setup_error_logging(
    log_path: str | os.PathLike[str] | None = None,
    *,
    level: str | int | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Configure runtime error logging to a rotating file.

    Should be called once at application startup (alongside ``load_env()``),
    before any work that might fail. Both the CLI (``pyagent_coding_agent``)
    and the server (``pyagent_server``) call this automatically.

    Args:
        log_path: Path to the error log file. When ``None`` (the default),
            reads ``PYAGENT_ERROR_LOG_PATH`` from the environment, falling back
            to ``.pyagent/error.log``. Parent directories are created
            automatically.
        level: Minimum level written to the file. When ``None``, reads
            ``PYAGENT_ERROR_LOG_LEVEL`` from the environment, falling back to
            ``"ERROR"``. Accepts a level name (``"ERROR"``, ``"WARNING"`` ...)
            or numeric value.
        max_bytes: Max size of each log file before rotation. Defaults to 5 MB.
        backup_count: Number of rotated backup files to keep. Defaults to 3.
            Combined with ``max_bytes``, the error log is bounded to roughly
            ``max_bytes * (backup_count + 1)`` on disk.

    Returns:
        The root logger (with the error handler attached). Callers normally
        ignore the return value and just use ``logging.getLogger(__name__)``
        in their own modules.

    Notes:
        - Idempotent: calling it again (e.g. after a re-import) does not add a
          second handler. A repeat call with a *different* path/level replaces
          the existing handler.
        - The handler is attached to the root logger so that errors raised
          inside third-party libraries (which propagate to root by default)
          are captured too. The root logger's own level is left untouched;
          only the handler's level is set, so non-error output is unaffected.
        - A failure to set up logging (e.g. unwritable path) is reported via
          the standard logging system but never raised — error logging must
          never break the application it is supposed to observe.
    """
    root_logger = logging.getLogger()

    resolved_path = Path(
        log_path
        if log_path is not None
        else os.environ.get("PYAGENT_ERROR_LOG_PATH", DEFAULT_LOG_PATH)
    )
    resolved_level = _level_value(
        level if level is not None
        else os.environ.get("PYAGENT_ERROR_LOG_LEVEL", DEFAULT_LOG_LEVEL)
    )

    # Replace any previously installed pyagent error handler so a changed
    # path/level takes effect on repeat calls.
    existing = _existing_handler(root_logger)
    if existing is not None:
        # If nothing relevant changed, keep the existing handler and bail out.
        same_path = (
            isinstance(existing, RotatingFileHandler)
            and Path(existing.baseFilename) == resolved_path.resolve()
        )
        same_level = existing.level == resolved_level
        if same_path and same_level:
            return root_logger
        root_logger.removeHandler(existing)
        try:
            existing.close()
        except Exception:  # pragma: no cover - best-effort cleanup
            pass

    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            resolved_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    except OSError as exc:
        # Fall back to logging via the existing config (e.g. stderr) — never
        # let logging setup crash the application.
        logging.getLogger(__name__).warning(
            "Failed to set up error log file at %s: %s", resolved_path, exc
        )
        return root_logger

    handler.setLevel(resolved_level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    setattr(handler, _HANDLER_MARKER, True)
    root_logger.addHandler(handler)

    # Ensure the root logger's effective level lets the handler's records
    # through. The default (WARNING) already permits ERROR, but if a caller
    # configured a higher level we lower it to the handler's level so error
    # records are not filtered out before reaching the handler.
    if root_logger.level > resolved_level:
        root_logger.setLevel(resolved_level)

    return root_logger
