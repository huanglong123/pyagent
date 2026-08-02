"""
LangGraph node functions and routing logic.

These are the core building blocks of the agent graph:
- call_model: Invokes the LLM with the current message history.
- should_continue: Conditional edge that routes to tool execution or end.
- execute_tools: Executes any tool calls from the LLM response.

This mirrors pi-mono's agent loop in packages/agent which alternates
between LLM calls and tool execution until the LLM stops requesting tools.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pyagent_agent.state import AgentState

logger = logging.getLogger(__name__)


def call_model(state: AgentState) -> dict[str, Any]:
    """Call the LLM with the current conversation history.

    If tools are registered, binds them to the model for function calling.
    Returns updated messages list with the LLM's response appended.
    """
    model = state["model"]
    messages = state.get("messages", [])
    tools = state.get("tools")
    tools_enabled = tools is not None and len(tools.list_names()) > 0

    # Bind tools if available
    if tools_enabled:
        from langchain_core.tools import StructuredTool

        # Convert our ToolSpec list to LangChain StructuredTools
        langchain_tools = []
        for spec in tools._tools.values():
            langchain_tools.append(
                StructuredTool.from_function(
                    name=spec.name,
                    description=spec.description,
                    args_schema=None,
                    func=spec.func,
                )
            )
        try:
            model = model.bind_tools(langchain_tools)
        except Exception as e:
            logger.warning("Failed to bind tools: %s", e)

    # Invoke the model
    response = model.invoke(messages)

    # Convert response to message dict
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                # Use langchain's native ToolCall shape ({"type", "name", "args",
                # "id"}). The "args" key (not "arguments") is required: when this
                # assistant message is fed back into model.invoke() on the next
                # loop iteration, langchain rebuilds the AIMessage via
                # create_tool_call(**tc), which only accepts name/args/id and
                # raises "tool_call() got an unexpected keyword argument
                # 'arguments'" if the OpenAI-style "arguments" key is used.
                tool_calls.append({
                    "type": "tool_call",
                    "id": tc.get("id", ""),
                    "name": tc.get("name", ""),
                    "args": tc.get("args", {}),
                })
        msg_dict: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            msg_dict["tool_calls"] = tool_calls
        return {"messages": messages + [msg_dict]}

    # Fallback: treat as plain text
    msg_dict = {"role": "assistant", "content": str(response)}
    return {"messages": messages + [msg_dict]}


def should_continue(state: AgentState) -> str:
    """Conditional edge: decide whether to continue with tools or end.

    Returns "tools" if the last message contains tool calls (and we haven't
    exceeded max iterations), otherwise returns "__end__".
    """
    messages = state.get("messages", [])
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 10)

    if iteration >= max_iterations:
        logger.warning("Max iterations (%d) reached, stopping", max_iterations)
        return "__end__"

    if not messages:
        return "__end__"

    last_msg = messages[-1]
    tool_calls = last_msg.get("tool_calls", [])

    if tool_calls:
        return "tools"
    return "__end__"


def execute_tools(state: AgentState) -> dict[str, Any]:
    """Execute any tool calls from the last LLM response.

    Appends tool result messages to the conversation history.
    Increments the iteration counter.
    """
    messages = state.get("messages", [])
    tools = state.get("tools")
    iteration = state.get("iteration", 0)

    if not messages or not tools:
        return {"messages": messages, "iteration": iteration}

    last_msg = messages[-1]
    tool_calls = last_msg.get("tool_calls", [])

    tool_results = []
    for tc in tool_calls:
        tool_name = tc.get("name", "")
        # Read the langchain-native "args" key (falls back to "arguments" for
        # any externally-produced tool calls that still use the OpenAI shape).
        tool_args = tc.get("args", tc.get("arguments", {}))
        tool_call_id = tc.get("id", "")

        logger.info("Executing tool: %s with args: %s", tool_name, tool_args)
        result = tools.execute(tool_name, tool_args)
        tool_results.append(result)

        messages.append({
            "role": "tool",
            "content": result,
            "tool_call_id": tool_call_id,
            "name": tool_name,
        })

    return {
        "messages": messages,
        "tool_results": tool_results,
        "iteration": iteration + 1,
    }
