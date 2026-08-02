"""
Screen management for the PyAgent TUI.

Provides custom screens for settings, help, and tool management.
"""

from __future__ import annotations

from textual.screen import ModalScreen
from textual.widgets import Static
from textual.containers import Vertical


class HelpScreen(ModalScreen):
    """Modal screen showing help and keyboard shortcuts."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-content {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        background: $surface;
    }
    """

    def compose(self) -> object:
        yield Vertical(
            Static(
                "[bold]PyAgent Help[/]\n\n"
                "[bold]Commands:[/]\n"
                "  /exit, /quit  - Exit the application\n"
                "  /clear        - Clear conversation history\n"
                "  /help         - Show this help screen\n"
                "\n[bold]Keyboard:[/]\n"
                "  Ctrl+C        - Exit immediately\n"
                "  Escape        - Close modal screens\n"
            ),
            id="help-content",
        )

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss()
