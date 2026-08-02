"""
Pydantic message models for the agent protocol.

These types define the wire format for all communication between the CLI,
TUI, client, and server. They are the Python equivalent of pi-mono's
packages/protocol TypeScript types.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Role of a message in the conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """A single message in the conversation history."""

    role: MessageRole
    content: str = ""
    name: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None

    def to_langchain(self) -> dict[str, Any]:
        """Convert to a LangChain message dict."""
        base: dict[str, Any] = {"role": self.role.value, "content": self.content}
        if self.name:
            base["name"] = self.name
        if self.tool_calls:
            base["tool_calls"] = [tc.model_dump() for tc in self.tool_calls]
        if self.tool_call_id:
            base["tool_call_id"] = self.tool_call_id
        return base


class ToolCall(BaseModel):
    """A tool/function call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of executing a tool call."""

    tool_call_id: str
    content: str
    is_error: bool = False


class SessionEventType(str, Enum):
    """Types of events emitted during an agent session."""

    MESSAGE_START = "message_start"
    MESSAGE_DELTA = "message_delta"
    MESSAGE_END = "message_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    ERROR = "error"
    DONE = "done"


class SessionRequest(BaseModel):
    """A request to start or continue an agent session."""

    session_id: str | None = None
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    provider: str | None = None
    tools_enabled: bool = True
    max_iterations: int = 10
    history: list[Message] = Field(default_factory=list)


class SessionResponse(BaseModel):
    """A response from an agent session (non-streaming)."""

    session_id: str
    messages: list[Message]
    tool_results: list[ToolResult] = Field(default_factory=list)


class SessionEvent(BaseModel):
    """A streaming event from an agent session."""

    type: SessionEventType
    session_id: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""

    def to_line(self) -> str:
        """Serialize to a single JSON line for NDJSON streaming."""
        import json

        return json.dumps(self.model_dump(), default=str)
