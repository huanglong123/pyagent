"""
Textual-based terminal UI for the PyAgent.

Provides an interactive chat interface with:
  - Message history display (scrollable)
  - Input box at the bottom
  - Real-time streaming response display
  - Model/provider status bar

Mirrors pi-mono's TUI which provides a similar interactive coding
agent interface in the terminal.
"""

from __future__ import annotations

import logging
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import (
    Header,
    Footer,
    Input,
    RichLog,
    Static,
)
from textual.reactive import reactive
from rich.markdown import Markdown

from pyagent_ai import ProviderConfig, ProviderType, setup_error_logging
from pyagent_agent import AgentSession, ToolRegistry
from pyagent_coding_agent.tools.file_ops import register_file_tools
from pyagent_coding_agent.tools.shell import register_shell_tools

logger = logging.getLogger(__name__)


class AgentApp(App):
    """Textual app for interactive agent chat.

    Usage:
        app = AgentApp(config=ProviderConfig(...))
        app.run()
    """

    TITLE = "PyAgent"
    SUB_TITLE = "AI Coding Agent"
    CSS = """
    #message-log {
        border: solid $primary;
        height: 1fr;
    }
    #input-bar {
        height: 3;
        dock: bottom;
    }
    #status-bar {
        height: 1;
        dock: bottom;
        background: $surface;
        color: $text-muted;
    }
    """

    model_name: reactive[str] = reactive("gpt-4o-mini")
    provider_name: reactive[str] = reactive("openai")

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__()
        # Set up runtime error logging once per TUI process (idempotent).
        setup_error_logging()
        self.config = config or ProviderConfig()
        self.model_name = self.config.model
        self.provider_name = self.config.provider.value
        self._session: AgentSession | None = None

    def _ensure_session(self) -> AgentSession:
        if self._session is None:
            registry = ToolRegistry()
            register_file_tools(registry)
            register_shell_tools(registry)
            self._session = AgentSession(
                model_config=self.config,
                tools=registry,
            )
        return self._session

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="message-log", markup=True)
        yield Horizontal(
            Input(placeholder="Type your message... (or /exit to quit)", id="msg-input"),
            id="input-bar",
        )
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        self._update_status()
        log = self.query_one("#message-log", RichLog)
        log.write("[bold cyan]PyAgent[/] - AI Coding Agent")
        log.write("[dim]Type your message below. Use /exit to quit, /clear to reset.[/]")
        log.write("")

    def _update_status(self) -> None:
        status = self.query_one("#status-bar", Static)
        status.update(
            f" Model: {self.model_name} | Provider: {self.provider_name} | "
            f"Tools: {'enabled' if self._session else 'disabled'}"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the input box."""
        text = event.value.strip()
        if not text:
            return

        # Clear input
        event.input.value = ""

        log = self.query_one("#message-log", RichLog)

        # Handle commands
        if text.lower() in ("/exit", "/quit"):
            self.exit()
            return
        elif text.lower() == "/clear":
            session = self._ensure_session()
            session.reset()
            log.write("[dim]Conversation cleared.[/]")
            return

        # Display user message
        log.write(f"[bold green]user>[/] {text}")

        # Run agent
        session = self._ensure_session()
        try:
            response = session.run(text)
            # Display response as markdown
            log.write(Markdown(response))
            log.write("")
        except Exception as e:
            # Persist the full traceback to the error log file.
            logger.exception("TUI turn failed")
            log.write(f"[red]Error: {e}[/]")
