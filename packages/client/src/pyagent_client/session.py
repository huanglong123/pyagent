"""
Remote session client for the pyagent-server.

Uses httpx to communicate with a FastAPI-based session server.
Supports both synchronous and asynchronous usage patterns.

Mirrors pi-mono's RemoteClient which connects to the session server
via WebSocket or HTTP and streams agent events.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from pyagent_protocol import SessionRequest, SessionResponse, Message


class RemoteSession:
    """Client for a remote pyagent-server instance.

    Usage:
        client = RemoteSession("http://localhost:8765")
        response = client.send_prompt("What is 2+2?")
        print(response)
    """

    def __init__(self, server_url: str) -> None:
        self.server_url = server_url.rstrip("/")
        self._client = httpx.Client(timeout=120.0)
        self._session_id: str | None = None

    def send_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Send a prompt to the remote server and return the response.

        Maintains session ID for multi-turn conversation across calls.
        """
        request = SessionRequest(
            session_id=self._session_id,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
        )

        response = self._client.post(
            f"{self.server_url}/api/session",
            json=request.model_dump(),
        )
        response.raise_for_status()

        data = response.json()
        result = SessionResponse.model_validate(data)
        self._session_id = result.session_id

        # Return the last assistant message
        for msg in reversed(result.messages):
            if msg.role.value == "assistant" and msg.content:
                return msg.content

        return "No response generated."

    async def asend_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Async version of send_prompt."""
        request = SessionRequest(
            session_id=self._session_id,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.server_url}/api/session",
                json=request.model_dump(),
            )
            response.raise_for_status()

        data = response.json()
        result = SessionResponse.model_validate(data)
        self._session_id = result.session_id

        for msg in reversed(result.messages):
            if msg.role.value == "assistant" and msg.content:
                return msg.content

        return "No response generated."

    def stream_prompt(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> Any:
        """Stream agent events from the remote server as NDJSON lines.

        Yields SessionEvent objects.
        """
        from pyagent_protocol import SessionEvent

        request = SessionRequest(
            session_id=self._session_id,
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            provider=provider,
        )

        with self._client.stream(
            "POST",
            f"{self.server_url}/api/session/stream",
            json=request.model_dump(),
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.strip():
                    data = json.loads(line)
                    yield SessionEvent.model_validate(data)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "RemoteSession":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
