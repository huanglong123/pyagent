"""
Streaming response handler.

Wraps LangChain's streaming interface to provide a unified chunk type
and async iterator pattern. This mirrors pi-mono's streaming abstraction
in packages/ai which normalizes provider-specific stream formats.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamChunk:
    """A single chunk from a streaming LLM response.

    content: Text content delta (may be empty for tool-call chunks).
    tool_call: Tool call data if this chunk contains a tool call.
    is_final: True if this is the last chunk.
    metadata: Additional provider-specific metadata.
    """

    content: str = ""
    tool_call: dict[str, Any] | None = None
    is_final: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class StreamHandler:
    """Handles streaming responses from LangChain chat models.

    Wraps the model's .stream() or .astream() method and normalizes
    the output into StreamChunk objects for the agent loop to consume.
    """

    def __init__(self, model: Any):
        self.model = model

    def stream(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Synchronously stream a response.

        Returns a LangChain stream iterator. Use this for sync contexts.
        """
        return self.model.stream(messages, **kwargs)

    async def astream(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncIterator[StreamChunk]:
        """Asynchronously stream a response as StreamChunk objects.

        This is the primary streaming method for the agent loop.
        """
        accumulated_content = ""
        async for chunk in self.model.astream(messages, **kwargs):
            text = ""
            if hasattr(chunk, "content"):
                content = chunk.content
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text = part.get("text", "")
            accumulated_content += text
            yield StreamChunk(content=text, is_final=False)

        yield StreamChunk(content="", is_final=True, metadata={"full_text": accumulated_content})
