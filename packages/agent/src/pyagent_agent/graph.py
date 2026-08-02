"""
LangGraph StateGraph construction.

Builds the agent graph with the following topology:

    START -> call_model -> should_continue
                              |
                    +---------+---------+
                    |                   |
                 "tools"             "__end__"
                    |
              execute_tools
                    |
                    v
              call_model (loop back)

This mirrors pi-mono's agent loop architecture where the LLM is called,
checked for tool calls, tools are executed, and results feed back into
the next LLM call until no more tool calls are needed.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph, START

from pyagent_agent.state import AgentState
from pyagent_agent.nodes import call_model, should_continue, execute_tools


def build_agent_graph() -> Any:
    """Build and compile the LangGraph agent graph.

    Returns a compiled graph that can be invoked with an AgentState.
    The graph implements the standard ReAct pattern:
    Reason -> Act (tool call) -> Observe (tool result) -> loop.
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("call_model", call_model)
    graph.add_node("execute_tools", execute_tools)

    # Set entry point
    graph.add_edge(START, "call_model")

    # Conditional edge after LLM call
    graph.add_conditional_edges(
        "call_model",
        should_continue,
        {
            "tools": "execute_tools",
            "__end__": END,
        },
    )

    # After tool execution, loop back to LLM call
    graph.add_edge("execute_tools", "call_model")

    return graph.compile()


class AgentGraph:
    """Wrapper around the compiled LangGraph for easier usage.

    Provides a clean invoke interface and manages state updates.
    """

    def __init__(self) -> None:
        self._graph = build_agent_graph()

    def invoke(self, state: AgentState) -> AgentState:
        """Run the agent graph to completion with the given state.

        The graph will loop between call_model and execute_tools until
        the LLM stops requesting tool calls or max_iterations is reached.
        """
        result = self._graph.invoke(state)
        return result  # type: ignore[no-any-return]

    async def ainvoke(self, state: AgentState) -> AgentState:
        """Async version of invoke."""
        result = await self._graph.ainvoke(state)
        return result  # type: ignore[no-any-return]

    def stream(self, state: AgentState) -> Any:
        """Stream graph execution, yielding state updates at each node."""
        yield from self._graph.stream(state)

    async def astream(self, state: AgentState) -> Any:
        """Async stream graph execution."""
        async for chunk in self._graph.astream(state):
            yield chunk
