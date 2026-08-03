"""
AgentSession — orchestrates the full agent loop.

This is the high-level entry point that ties together the LLM model,
tool registry, and LangGraph state machine. It manages conversation
history, session state, and provides both sync and async invocation.

Mirrors pi-mono's AgentSession which is the primary API consumed by
the coding-agent CLI, TUI, and server.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from pyagent_ai import ProviderConfig, get_chat_model
from pyagent_ai.tracing import (
    TraceMetadata,
    get_config as get_tracing_config,
    measure_latency,
)
from pyagent_agent.graph import AgentGraph
from pyagent_agent.state import AgentState, create_initial_state
from pyagent_agent.tools import ToolRegistry
from pyagent_protocol import Message

logger = logging.getLogger(__name__)


class AgentSession:
    """Manages a single agent conversation session.

    Usage:
        session = AgentSession(model_config=ProviderConfig(...))
        session.register_tool("read_file", "Read a file", read_file_fn)
        response = session.run("What files are in this directory?")
        print(response)
    """

    def __init__(
        self,
        model_config: ProviderConfig | None = None,
        system_prompt: str | None = None,
        tools: ToolRegistry | None = None,
        max_iterations: int = 10,
    ) -> None:
        self.session_id = str(uuid.uuid4())
        self.model_config = model_config or ProviderConfig()
        self.system_prompt = system_prompt or (
            "You are a helpful coding assistant. "
            "Use tools when appropriate to complete tasks. "
            "Be concise and direct."
        )
        self.tools = tools or ToolRegistry()
        self.max_iterations = max_iterations

        # Lazily initialized
        self._model: Any = None
        self._graph: AgentGraph | None = None
        self._history: list[dict[str, Any]] = []

        # --- LangSmith tracing metadata ---
        self._tracing_meta = TraceMetadata(
            session_id=self.session_id,
            model=self.model_config.model,
            provider=self.model_config.provider.value
            if hasattr(self.model_config.provider, "value")
            else str(self.model_config.provider),
        )

    def _ensure_initialized(self) -> None:
        """Lazily initialize the model and graph."""
        if self._model is None:
            self._model = get_chat_model(self.model_config)
        if self._graph is None:
            self._graph = AgentGraph()

    def register_tool(
        self,
        name: str,
        description: str,
        func: Any,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """Register a tool for the agent to use."""
        self.tools.register(name, description, func, parameters)

    @staticmethod
    def _extract_response(messages: list[dict[str, Any]]) -> str:
        """Extract the last assistant message from a messages list."""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        return "No response generated."

    def run(self, prompt: str) -> str:
        """Run a single turn of the agent loop.

        Adds the user's prompt to the conversation, runs the LangGraph
        agent to completion, and returns the assistant's final response.

        When LangSmith tracing is enabled, the entire execution is
        wrapped in a traceable span with metadata (session_id, model,
        provider) injected for filtering in the LangSmith UI.
        """
        self._ensure_initialized()
        assert self._model is not None
        assert self._graph is not None

        self._history.append({"role": "user", "content": prompt})

        state = create_initial_state(
            model=self._model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            history=list(self._history),
            max_iterations=self.max_iterations,
        )

        tracing_cfg = get_tracing_config()

        if tracing_cfg.enabled:
            return self._run_with_tracing(state, prompt)

        # Fast path — no tracing
        result_state = self._graph.invoke(state)
        messages = result_state.get("messages", [])
        self._history = messages
        return self._extract_response(messages)

    def _run_with_tracing(self, state: AgentState, prompt: str) -> str:
        """Execute the agent loop wrapped in LangSmith tracing."""
        from pyagent_ai.tracing import current_metadata, push_metadata, pop_metadata

        push_metadata(self._tracing_meta)

        try:
            # Create a top-level traceable span for this agent run
            from langsmith.run_helpers import traceable

            @traceable(
                name="agent-run",
                tags=["agent", self.model_config.provider.value if hasattr(self.model_config.provider, "value") else str(self.model_config.provider)],
            )
            def _execute(agent_state: AgentState, user_prompt: str) -> str:
                with measure_latency("agent_total") as metrics:
                    result = self._graph.invoke(agent_state)
                messages = result.get("messages", [])
                self._history = messages
                resp = self._extract_response(messages)
                # Inject latency into metadata for this span
                meta = current_metadata()
                meta["total_duration_ms"] = metrics["duration_ms"]
                return resp

            return _execute(state, prompt)
        except Exception:
            logger.exception("Agent run failed during traced execution")
            raise
        finally:
            pop_metadata()

    async def arun(self, prompt: str) -> str:
        """Async version of run."""
        self._ensure_initialized()
        assert self._model is not None
        assert self._graph is not None

        self._history.append({"role": "user", "content": prompt})

        state = create_initial_state(
            model=self._model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            history=list(self._history),
            max_iterations=self.max_iterations,
        )

        tracing_cfg = get_tracing_config()

        if tracing_cfg.enabled:
            return await self._arun_with_tracing(state, prompt)

        result_state = await self._graph.ainvoke(state)
        messages = result_state.get("messages", [])
        self._history = messages
        return self._extract_response(messages)

    async def _arun_with_tracing(self, state: AgentState, prompt: str) -> str:
        """Async version of _run_with_tracing."""
        from pyagent_ai.tracing import current_metadata, push_metadata, pop_metadata

        push_metadata(self._tracing_meta)

        try:
            from langsmith.run_helpers import traceable

            @traceable(
                name="agent-run-async",
                tags=["agent", "async"],
            )
            async def _execute_async(agent_state: AgentState, user_prompt: str) -> str:
                with measure_latency("agent_total") as metrics:
                    result = await self._graph.ainvoke(agent_state)
                messages = result.get("messages", [])
                self._history = messages
                resp = self._extract_response(messages)
                meta = current_metadata()
                meta["total_duration_ms"] = metrics["duration_ms"]
                return resp

            return await _execute_async(state, prompt)
        except Exception:
            logger.exception("Agent async run failed during traced execution")
            raise
        finally:
            pop_metadata()

    def stream(self, prompt: str) -> Any:
        """Run the agent with streaming, yielding state updates at each node.

        Each yielded chunk is a dict mapping node name to state delta.
        When tracing is enabled, the overall stream is wrapped in a
        traceable span.
        """
        self._ensure_initialized()
        assert self._model is not None
        assert self._graph is not None

        self._history.append({"role": "user", "content": prompt})

        state = create_initial_state(
            model=self._model,
            tools=self.tools,
            system_prompt=self.system_prompt,
            history=list(self._history),
            max_iterations=self.max_iterations,
        )

        tracing_cfg = get_tracing_config()

        if tracing_cfg.enabled:
            yield from self._stream_with_tracing(state)
        else:
            final_messages: list[dict[str, Any]] = []
            for chunk in self._graph.stream(state):
                for node_name, state_delta in chunk.items():
                    if "messages" in state_delta:
                        final_messages = state_delta["messages"]
                    yield node_name, state_delta

            if final_messages:
                self._history = final_messages

    def _stream_with_tracing(self, state: AgentState) -> Any:
        """Streaming with LangSmith tracing."""
        from pyagent_ai.tracing import push_metadata, pop_metadata

        push_metadata(self._tracing_meta)
        try:
            from langsmith.run_helpers import traceable

            @traceable(name="agent-stream", tags=["agent", "stream"])
            def _do_stream(agent_state: AgentState) -> list[dict[str, Any]]:
                final_messages: list[dict[str, Any]] = []
                for chunk in self._graph.stream(agent_state):
                    for node_name, state_delta in chunk.items():
                        if "messages" in state_delta:
                            final_messages = state_delta["messages"]
                return final_messages

            final_messages = _do_stream(state)
            if final_messages:
                self._history = final_messages

            # Re-yield the actual stream data for the caller
            for chunk in self._graph.stream(state):
                for node_name, state_delta in chunk.items():
                    yield node_name, state_delta
        except Exception:
            logger.exception("Traced stream failed")
            raise
        finally:
            pop_metadata()

    def get_history(self) -> list[Message]:
        """Get conversation history as protocol Message objects."""
        return [Message(**msg) if isinstance(msg, dict) else msg for msg in self._history]

    def reset(self) -> None:
        """Clear conversation history, keeping the model and tools."""
        self._history = []
