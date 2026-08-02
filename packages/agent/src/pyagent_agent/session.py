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

    def run(self, prompt: str) -> str:
        """Run a single turn of the agent loop.

        Adds the user's prompt to the conversation, runs the LangGraph
        agent to completion, and returns the assistant's final response.
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

        result_state = self._graph.invoke(state)
        messages = result_state.get("messages", [])

        # Update history with the full conversation from the graph
        self._history = messages

        # Extract the last assistant message for the response
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return msg.get("content", "")

        return "No response generated."

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

        result_state = await self._graph.ainvoke(state)
        messages = result_state.get("messages", [])
        self._history = messages

        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return msg.get("content", "")

        return "No response generated."

    def stream(self, prompt: str) -> Any:
        """Run the agent with streaming, yielding state updates at each node.

        Each yielded chunk is a dict mapping node name to state delta.
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

        final_messages: list[dict[str, Any]] = []
        for chunk in self._graph.stream(state):
            for node_name, state_delta in chunk.items():
                if "messages" in state_delta:
                    final_messages = state_delta["messages"]
                yield node_name, state_delta

        if final_messages:
            self._history = final_messages

    def get_history(self) -> list[Message]:
        """Get conversation history as protocol Message objects."""
        return [Message(**msg) if isinstance(msg, dict) else msg for msg in self._history]

    def reset(self) -> None:
        """Clear conversation history, keeping the model and tools."""
        self._history = []
