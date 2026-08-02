"""
SQLModel table definitions for session persistence.

Defines the database schema for storing agent sessions, messages,
and tool execution results. Mirrors pi-mono's storage schema in
packages/storage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlmodel import Field, SQLModel


class SessionRecord(SQLModel, table=True):
    """A stored agent session."""

    __tablename__ = "sessions"

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    system_prompt: str | None = None
    model_provider: str = "openai"
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7


class MessageRecord(SQLModel, table=True):
    """A single message within a session."""

    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    role: str  # system, user, assistant, tool
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    seq: int = 0  # ordering within the session


class ToolResultRecord(SQLModel, table=True):
    """Result of a tool execution within a session."""

    __tablename__ = "tool_results"

    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.id", index=True)
    tool_call_id: str = ""
    tool_name: str = ""
    arguments: str = ""  # JSON string
    result: str = ""
    is_error: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
