"""
Agent state definition for LangGraph.

Defines the TypedDict that flows through the LangGraph StateGraph.
This mirrors pi-mono's AgentState / SessionState which tracks the
conversation history, tool results, and iteration count.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """State that flows through the LangGraph agent graph.

    messages: The conversation history as LangChain message dicts.
    tool_results: Results from tool executions in the current turn.
    iteration: Current iteration count (for max-iteration safety).
    max_iterations: Safety limit on agent loop iterations.
    model: The LangChain chat model instance to use.
    tools: The ToolRegistry containing available tools.
    system_prompt: Optional system prompt for the conversation.
    error: Error message if the agent encountered an issue.
    """

    messages: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    iteration: int
    max_iterations: int
    model: Any
    tools: Any  # ToolRegistry
    system_prompt: str | None
    error: str | None


def create_initial_state(
    model: Any,
    tools: Any,
    system_prompt: str | None = None,
    history: list[dict[str, Any]] | None = None,
    max_iterations: int = 10,
) -> AgentState:
    """Create the initial agent state for a new session.

    Args:
        model: A LangChain chat model instance.
        tools: A ToolRegistry with available tools.
        system_prompt: Optional system prompt to prepend.
        history: Existing conversation history (list of message dicts).
        max_iterations: Safety limit on agent loop iterations.

    Returns:
        Initial AgentState dict.
    """
    messages: list[dict[str, Any]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        messages.extend(history)
    return {
        "messages": messages,
        "tool_results": [],
        "iteration": 0,
        "max_iterations": max_iterations,
        "model": model,
        "tools": tools,
        "system_prompt": system_prompt,
        "error": None,
    }
