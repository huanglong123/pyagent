"""
Environment loading utilities.

Loads configuration from a ``.env`` file into ``os.environ`` so that the
existing environment-variable-based configuration (API keys, model settings,
storage path, etc.) picks up values from the file automatically — no need to
change every ``os.environ.get()`` call site.

Precedence (highest to lowest):
    1. Real environment variables already set in the shell
    2. Values defined in the ``.env`` file
    3. Hard-coded defaults in each config reader

By default ``load_env()`` does NOT override variables already present in the
environment, so exporting a variable in the shell always wins over a value in
the ``.env`` file. This mirrors the default behaviour of ``python-dotenv``.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_env(
    env_file: str | os.PathLike[str] | None = None,
    *,
    override: bool = False,
) -> bool:
    """Load environment variables from a ``.env`` file.

    This should be called once at application startup (e.g. at the top of the
    CLI entry point and the server module) before any configuration is read,
    so that downstream ``os.environ.get(...)`` calls see the loaded values.

    Args:
        env_file: Optional explicit path to a ``.env`` file. When ``None``
            (the default), ``python-dotenv`` searches for a ``.env`` file
            starting from the current working directory and walking up the
            directory tree — convenient when running from a project
            subdirectory.
        override: When ``True``, values from the ``.env`` file overwrite
            variables already set in the environment. Defaults to ``False``
            so real environment variables always take precedence over the
            ``.env`` file.

    Returns:
        ``True`` if a ``.env`` file was found and loaded, ``False`` otherwise.
        A ``False`` return value is not an error — it simply means no
        ``.env`` file was present, and configuration falls back to real
        environment variables and defaults.
    """
    if env_file is not None:
        return load_dotenv(Path(env_file), override=override)
    return load_dotenv(override=override)
