"""
File operation tools for the coding agent.

Provides tools for reading, writing, listing, and searching files.
These are the Python equivalents of pi-mono's file operation tools
in packages/coding-agent.
"""

from __future__ import annotations

import os
from pyagent_agent.tools import ToolRegistry


def _read_file(path: str) -> str:
    """Read a file's contents. Returns error string on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


def _write_file(path: str, content: str) -> str:
    """Write content to a file, creating directories as needed."""
    try:
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def _list_directory(path: str = ".") -> str:
    """List directory contents."""
    try:
        entries = sorted(os.listdir(path))
        result = []
        for entry in entries:
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                result.append(f"  {entry}/")
            else:
                size = os.path.getsize(full)
                result.append(f"  {entry} ({size} bytes)")
        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"


def _file_exists(path: str) -> str:
    """Check if a file or directory exists."""
    exists = os.path.exists(path)
    is_dir = os.path.isdir(path) if exists else False
    return f"{'exists' if exists else 'not found'}{' (directory)' if is_dir else ''}"


def register_file_tools(registry: ToolRegistry) -> None:
    """Register all file operation tools into the given registry."""
    registry.register(
        name="read_file",
        description="Read the contents of a file at the given path.",
        func=_read_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
            },
            "required": ["path"],
        },
    )
    registry.register(
        name="write_file",
        description="Write content to a file at the given path. Creates directories as needed.",
        func=_write_file,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    )
    registry.register(
        name="list_directory",
        description="List the contents of a directory.",
        func=_list_directory,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path. Defaults to current directory."},
            },
        },
    )
    registry.register(
        name="file_exists",
        description="Check if a file or directory exists at the given path.",
        func=_file_exists,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to check"},
            },
            "required": ["path"],
        },
    )
