"""
Shell command execution tool for the coding agent.

Provides a tool for running shell commands. Includes safety measures:
a timeout and output truncation. Mirrors pi-mono's shell/bash tool
in packages/coding-agent.
"""

from __future__ import annotations

import subprocess

from pyagent_agent.tools import ToolRegistry

# Safety limits
_MAX_OUTPUT = 10000  # characters
_DEFAULT_TIMEOUT = 30  # seconds


def _run_command(command: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Execute a shell command and return its output.

    Args:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"

        if len(output) > _MAX_OUTPUT:
            output = output[:_MAX_OUTPUT] + f"\n... (truncated, {len(output) - _MAX_OUTPUT} more chars)"

        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"


def register_shell_tools(registry: ToolRegistry) -> None:
    """Register shell command tools into the given registry."""
    registry.register(
        name="run_command",
        description="Execute a shell command and return its output. Use for file operations, git, builds, etc.",
        func=_run_command,
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute"},
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default: {_DEFAULT_TIMEOUT})",
                },
            },
            "required": ["command"],
        },
    )
