"""
Mode routing — interactive / pipe / RPC.

Each mode wraps the AgentSession with different I/O strategies:
  - Pipe: single prompt in, single response out (stdout).
  - Interactive: REPL loop with rich rendering, multi-turn conversation.
  - RPC: connects to a remote pyagent-server via HTTP (uses pyagent-client).

Mirrors pi-mono's mode system in packages/coding-agent which supports
the same three execution modes.
"""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from pyagent_ai import ProviderConfig
from pyagent_agent import AgentSession, ToolRegistry
from pyagent_coding_agent.tools.file_ops import register_file_tools
from pyagent_coding_agent.tools.shell import register_shell_tools


def _create_session(
    config: ProviderConfig,
    system_prompt: str | None,
    tools_enabled: bool,
    max_iterations: int,
) -> AgentSession:
    """Create an AgentSession with built-in tools registered."""
    registry = ToolRegistry()

    if tools_enabled:
        register_file_tools(registry)
        register_shell_tools(registry)

    session = AgentSession(
        model_config=config,
        system_prompt=system_prompt,
        tools=registry,
        max_iterations=max_iterations,
    )
    return session


def run_pipe_mode(
    prompt: str,
    config: ProviderConfig,
    system_prompt: str | None,
    tools_enabled: bool,
    max_iterations: int,
    console: Console,
) -> None:
    """Execute a single prompt and print the result to stdout.

    This mode is designed for scripting: input via argument, output to stdout.
    Tool execution details are printed to stderr so stdout stays clean.
    """
    session = _create_session(config, system_prompt, tools_enabled, max_iterations)

    # Stream the agent, showing tool calls on stderr
    for node_name, state_delta in session.stream(prompt):
        if node_name == "execute_tools":
            tool_results = state_delta.get("tool_results", [])
            for tr in tool_results:
                console.print(f"[dim][tool] {tr[:200]}...[/]", style="dim")

    # Get the final response from history
    history = session.get_history()
    for msg in reversed(history):
        if msg.role.value == "assistant" and msg.content:
            console.print(msg.content)
            return

    console.print("No response generated.", style="red")


def run_interactive_mode(
    config: ProviderConfig,
    system_prompt: str | None,
    tools_enabled: bool,
    max_iterations: int,
    console: Console,
) -> None:
    """Run an interactive REPL with multi-turn conversation.

    Supports:
      - Multi-turn conversation (history is maintained)
      - Rich markdown rendering of responses
      - Tool call display
      - Commands: /exit, /clear, /help
    """
    session = _create_session(config, system_prompt, tools_enabled, max_iterations)

    console.print("[dim]Type /exit to quit, /clear to reset conversation, /help for commands.[/]")
    console.print()

    while True:
        try:
            user_input = Prompt.ask("[bold green]user[/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/]")
            break

        if not user_input.strip():
            continue

        # Handle commands
        if user_input.strip().lower() in ("/exit", "/quit"):
            console.print("[dim]Goodbye![/]")
            break
        elif user_input.strip().lower() == "/clear":
            session.reset()
            console.print("[dim]Conversation cleared.[/]")
            continue
        elif user_input.strip().lower() == "/help":
            console.print(
                Panel(
                    "[bold]/exit[/] or [bold]/quit[/] - Exit the session\n"
                    "[bold]/clear[/] - Clear conversation history\n"
                    "[bold]/help[/] - Show this help",
                    title="Commands",
                    border_style="cyan",
                )
            )
            continue

        # Run the agent
        console.print()
        try:
            response = session.run(user_input)
            console.print()
            console.print(Panel(Markdown(response), title="[bold blue]assistant[/]", border_style="blue"))
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
        console.print()


def run_rpc_mode(
    server_url: str,
    prompt: str | None,
    system_prompt: str | None,
    model: str | None,
    provider: str | None,
    console: Console,
) -> None:
    """Connect to a remote pyagent-server and send the prompt.

    Uses pyagent-client's RemoteSession to communicate over HTTP.
    Falls back to interactive mode if no prompt is provided.
    """
    try:
        from pyagent_client import RemoteSession
    except ImportError:
        console.print("[red]pyagent-client is not installed. Cannot use RPC mode.[/]")
        return

    session = RemoteSession(server_url)

    if prompt:
        response = session.send_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
        )
        console.print(Panel(Markdown(response), title="[bold blue]assistant[/]", border_style="blue"))
    else:
        console.print("[dim]RPC interactive mode. Type /exit to quit.[/]")
        while True:
            try:
                user_input = Prompt.ask("[bold green]user[/]")
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ("/exit", "/quit"):
                break
            response = session.send_prompt(
                prompt=user_input,
                system_prompt=system_prompt,
                model=model,
                provider=provider,
            )
            console.print()
            console.print(Panel(Markdown(response), title="[bold blue]assistant[/]", border_style="blue"))
            console.print()
