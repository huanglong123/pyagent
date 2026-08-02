"""
FastAPI application for the pyagent session server.

Provides REST endpoints for:
  - POST /api/session: Create or continue a session (returns full response)
  - POST /api/session/stream: Stream events as NDJSON
  - GET /api/session/{id}: Get session history
  - GET /api/health: Health check

Mirrors pi-mono's packages/server which provides the same session
management capabilities over HTTP.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI
from fastapi import HTTPException
from rich import print as rprint

from pyagent_ai import ProviderConfig, ProviderType, get_chat_model, load_env, setup_error_logging
from pyagent_agent import AgentSession, ToolRegistry
from pyagent_coding_agent.tools.file_ops import register_file_tools
from pyagent_coding_agent.tools.shell import register_shell_tools
from pyagent_protocol import SessionRequest, SessionResponse, Message, SessionEvent, SessionEventType

logger = logging.getLogger(__name__)

# Load configuration from a .env file (if present) before any request handler
# reads config. Real environment variables always take precedence over .env.
# Runs once at import time, so it applies regardless of how the app is started
# (e.g. `uvicorn pyagent_server.app:app`).
load_env()

# Set up runtime error logging to a rotating file (path/level configurable via
# PYAGENT_ERROR_LOG_PATH / PYAGENT_ERROR_LOG_LEVEL). Called right after
# load_env() so the env vars are visible.
setup_error_logging()

app = FastAPI(
    title="PyAgent Server",
    description="Session server for the PyAgent AI coding agent",
    version="0.1.0",
)

# In-memory session store (replace with pyagent-storage for persistence)
_sessions: dict[str, AgentSession] = {}


def create_app() -> FastAPI:
    """Factory function for creating the FastAPI app."""
    return app


def _get_or_create_session(
    session_id: str | None,
    request: SessionRequest,
) -> AgentSession:
    """Get an existing session or create a new one."""
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    # Build provider config
    provider = ProviderType(request.provider) if request.provider else ProviderType.OPENAI
    model = request.model or os.environ.get("PYAGENT_MODEL_NAME", "gpt-4o-mini")
    config = ProviderConfig(provider=provider, model=model)

    # Create tool registry with built-in tools
    registry = ToolRegistry()
    if request.tools_enabled:
        register_file_tools(registry)
        register_shell_tools(registry)

    session = AgentSession(
        model_config=config,
        system_prompt=request.system_prompt,
        tools=registry,
        max_iterations=request.max_iterations,
    )
    _sessions[session.session_id] = session
    return session


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "pyagent-server"}


@app.post("/api/session", response_model=SessionResponse)
async def create_session(request: SessionRequest) -> SessionResponse:
    """Create or continue a session. Returns the full conversation."""
    try:
        session = _get_or_create_session(request.session_id, request)
        await session.arun(request.prompt)
        messages = session.get_history()
        return SessionResponse(
            session_id=session.session_id,
            messages=messages,
        )
    except HTTPException:
        # Propagate HTTP-level errors (e.g. 404) untouched.
        raise
    except Exception:
        # Persist the full traceback, then return a clean 500 to the client.
        logger.exception("create_session failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/session/stream")
async def stream_session(request: SessionRequest) -> Any:
    """Stream agent events as NDJSON lines."""
    from fastapi.responses import StreamingResponse

    try:
        session = _get_or_create_session(request.session_id, request)
    except Exception:
        logger.exception("stream_session failed to create session")
        raise HTTPException(status_code=500, detail="Internal server error")

    async def event_stream():
        try:
            for node_name, state_delta in session.stream(request.prompt):
                if node_name == "execute_tools":
                    event = SessionEvent(
                        type=SessionEventType.TOOL_CALL_END,
                        session_id=session.session_id,
                        data={"results": state_delta.get("tool_results", [])},
                    )
                    yield event.to_line() + "\n"
                elif node_name == "call_model":
                    messages = state_delta.get("messages", [])
                    if messages:
                        last = messages[-1]
                        if last.get("role") == "assistant" and last.get("content"):
                            event = SessionEvent(
                                type=SessionEventType.MESSAGE_END,
                                session_id=session.session_id,
                                data={"content": last["content"]},
                            )
                            yield event.to_line() + "\n"

            done_event = SessionEvent(
                type=SessionEventType.DONE,
                session_id=session.session_id,
            )
            yield done_event.to_line() + "\n"
        except Exception:
            # Streaming has already begun (headers sent), so we cannot swap the
            # status code; persist the traceback and emit an error event line.
            logger.exception("stream_session event stream failed")
            err_event = SessionEvent(
                type=SessionEventType.ERROR,
                session_id=session.session_id,
                data={"error": "Internal server error"},
            )
            yield err_event.to_line() + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
    )


@app.get("/api/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get the history of an existing session."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    messages = session.get_history()
    return SessionResponse(session_id=session_id, messages=messages)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Run the server with uvicorn."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
