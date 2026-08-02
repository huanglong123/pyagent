"""
Custom Textual widgets for the PyAgent TUI.

Provides specialized widgets for rendering agent messages,
tool call indicators, and streaming text.
"""

from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive


class MessageWidget(Static):
    """A widget that displays a single conversation message."""

    role: reactive[str] = reactive("user")
    content: reactive[str] = reactive("")

    def __init__(self, role: str = "user", content: str = "") -> None:
        super().__init__()
        self.role = role
        self.content = content

    def watch_content(self, content: str) -> None:
        """Update display when content changes."""
        prefix = {"user": "[bold green]user>[/]", "assistant": "[bold blue]assistant>[/]"}.get(
            self.role, f"[bold]{self.role}>[/]"
        )
        self.update(f"{prefix} {content}")


class ToolCallIndicator(Static):
    """A widget that shows a tool call in progress."""

    tool_name: reactive[str] = reactive("")

    def __init__(self, tool_name: str = "") -> None:
        super().__init__()
        self.tool_name = tool_name

    def watch_tool_name(self, name: str) -> None:
        self.update(f"[dim yellow][tool] {name}...[/]")


class StatusBar(Static):
    """Status bar showing current model and provider info."""

    model: reactive[str] = reactive("gpt-4o-mini")
    provider: reactive[str] = reactive("openai")

    def watch_model(self, model: str) -> None:
        self._refresh()

    def watch_provider(self, provider: str) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.update(f" Model: {self.model} | Provider: {self.provider}")
