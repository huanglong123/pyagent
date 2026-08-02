"""
pyagent-protocol: Message models and serialization for cross-process communication.

Mirrors pi-mono's packages/protocol — defines the wire format for messages
exchanged between the CLI, TUI, client, and server.
"""

from pyagent_protocol.messages import (
    Message,
    MessageRole,
    ToolCall,
    ToolResult,
    SessionRequest,
    SessionResponse,
    SessionEvent,
    SessionEventType,
)
from pyagent_protocol.serialization import serialize, deserialize

__all__ = [
    "Message",
    "MessageRole",
    "ToolCall",
    "ToolResult",
    "SessionRequest",
    "SessionResponse",
    "SessionEvent",
    "SessionEventType",
    "serialize",
    "deserialize",
]
