"""
CLI application using typer + rich.

Provides three modes (mirrors pi-mono's coding-agent modes):
  - Interactive: REPL loop with rich console output
  - Pipe: single prompt -> stdout (for scripting)
  - RPC: connect to a remote pyagent-server instance

Usage:
  pyagent "What files are in this directory?"     # pipe mode
  pyagent                                          # interactive mode
  pyagent --interactive                            # explicit interactive
  pyagent --rpc http://localhost:8765 "prompt"     # RPC mode
  pyagent --model gpt-4o --provider openai         # model selection
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from pyagent_ai import ProviderConfig, ProviderType, load_env, setup_error_logging
from pyagent_ai.tracing import init_tracing
from pyagent_coding_agent.modes import run_pipe_mode, run_interactive_mode, run_rpc_mode

app = typer.Typer(
    name="pyagent",
    help="A Python AI coding agent harness built with LangGraph + LangChain.",
    no_args_is_help=False,
    add_completion=False,
)
console = Console()
logger = logging.getLogger(__name__)

# Preserve the original excepthook so a custom hook can delegate back to it
# after recording the crash, keeping the normal terminal traceback intact.
_default_excepthook = sys.excepthook


def _pyagent_excepthook(exc_type, exc_value, exc_tb) -> None:
    """Log uncaught exceptions to the error log file, then defer to default."""
    # KeyboardInterrupt is a normal exit path, not an error worth logging.
    if issubclass(exc_type, KeyboardInterrupt):
        _default_excepthook(exc_type, exc_value, exc_tb)
        return
    logger.critical(
        "Uncaught exception during CLI execution",
        exc_info=(exc_type, exc_value, exc_tb),
    )
    _default_excepthook(exc_type, exc_value, exc_tb)


def _install_excepthook() -> None:
    """Install the pyagent excepthook (idempotent)."""
    if sys.excepthook is not _pyagent_excepthook:
        sys.excepthook = _pyagent_excepthook


def _build_config(
    model: str | None,
    provider: str | None,
    temperature: float,
) -> ProviderConfig:
    """Build a ProviderConfig from CLI arguments and environment."""
    resolved_provider = ProviderType(
        provider or os.environ.get("PYAGENT_MODEL_PROVIDER", "openai")
    )
    resolved_model = model or os.environ.get("PYAGENT_MODEL_NAME", "gpt-4o-mini")
    return ProviderConfig(
        provider=resolved_provider,
        model=resolved_model,
        temperature=temperature,
    )


@app.command()
def main(
    prompt: Optional[str] = typer.Argument(
        None, help="Prompt text. If omitted, starts interactive mode."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Force interactive REPL mode."
    ),
    rpc: Optional[str] = typer.Option(
        None, "--rpc", help="Connect to a remote pyagent-server URL (RPC mode)."
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model name (e.g. gpt-4o-mini, claude-3-5-sonnet)."
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="LLM provider (openai/anthropic/google/ollama/openai_compatible/deepseek).",
    ),
    temperature: float = typer.Option(
        0.7, "--temperature", "-t", help="Sampling temperature."
    ),
    system: Optional[str] = typer.Option(
        None, "--system", "-s", help="Custom system prompt."
    ),
    no_tools: bool = typer.Option(
        False, "--no-tools", help="Disable tool calling."
    ),
    max_iterations: int = typer.Option(
        10, "--max-iterations", help="Maximum agent loop iterations."
    ),
    eval_mode: bool = typer.Option(
        False, "--eval", help="Run LangSmith-integrated evaluation suite."
    ),
) -> None:
    """Run the PyAgent coding agent."""

    # Load configuration from a .env file (if present) before reading any
    # config. Real environment variables always take precedence over .env.
    load_env()

    # Set up runtime error logging to a rotating file (path/level configurable
    # via PYAGENT_ERROR_LOG_PATH / PYAGENT_ERROR_LOG_LEVEL). Done right after
    # load_env() so the env vars are visible. Then install a global excepthook
    # as a safety net for any crash not caught by the mode handlers.
    setup_error_logging()
    _install_excepthook()

    # Initialise LangSmith tracing (no-op if LANGSMITH_TRACING is not true).
    # This wires up automatic tracing of all LangChain / LangGraph calls.
    init_tracing()

    # Evaluation mode: run the LangSmith-integrated evaluation suite
    if eval_mode:
        console.print(
            Panel(
                "[bold cyan]PyAgent Evaluation Suite[/]\n"
                "[dim]Running LangSmith-integrated evals...[/]",
                border_style="cyan",
            )
        )
        from pyagent_evals import run_langsmith_evals

        eval_config = _build_config(model, provider, temperature)
        run_langsmith_evals(config=eval_config, upload=True)
        return

    # Show banner
    console.print(
        Panel(
            "[bold cyan]PyAgent[/] - AI Coding Agent\n"
            "[dim]Built with LangGraph + LangChain[/]",
            border_style="cyan",
        )
    )

    # RPC mode: delegate to remote server
    if rpc:
        run_rpc_mode(rpc, prompt, system, model, provider, console)
        return

    # Build provider config
    config = _build_config(model, provider, temperature)

    # Pipe mode: prompt provided, no interactive flag
    if prompt and not interactive:
        run_pipe_mode(
            prompt=prompt,
            config=config,
            system_prompt=system,
            tools_enabled=not no_tools,
            max_iterations=max_iterations,
            console=console,
        )
        return

    # Interactive mode: no prompt, or explicit --interactive flag
    run_interactive_mode(
        config=config,
        system_prompt=system,
        tools_enabled=not no_tools,
        max_iterations=max_iterations,
        console=console,
    )


def cli_entry() -> None:
    """Entry point for console_scripts."""
    app()


if __name__ == "__main__":
    app()
