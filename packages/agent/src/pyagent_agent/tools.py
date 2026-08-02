"""
Tool registry and specification.

Provides a unified interface for registering and executing tools
within the agent loop. Tools are callable Python functions decorated
with metadata that LangGraph can bind to the LLM for function calling.

This mirrors pi-mono's ToolSpec interface in packages/agent.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, get_type_hints


@dataclass
class ToolSpec:
    """Specification for a single tool.

    name: The tool name as seen by the LLM.
    description: Description for the LLM to understand when to use it.
    func: The Python callable that executes the tool.
    parameters: JSON schema for the tool's parameters.
    """

    name: str
    description: str
    func: Callable[..., Any]
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_langchain(self) -> dict[str, Any]:
        """Convert to LangChain tool bind format."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def execute(self, arguments: dict[str, Any]) -> str:
        """Execute the tool with the given arguments."""
        try:
            result = self.func(**arguments)
            if not isinstance(result, str):
                result = json.dumps(result, default=str)
            return result
        except Exception as e:
            return json.dumps({"error": str(e)})


class ToolRegistry:
    """Registry of available tools for the agent.

    Tools are registered with .register() and looked up by name.
    The registry provides LangChain-compatible tool definitions for
    binding to the LLM model.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        parameters: dict[str, Any] | None = None,
    ) -> ToolSpec:
        """Register a new tool.

        If parameters is None, attempt to infer from the function signature.
        """
        if parameters is None:
            parameters = self._infer_parameters(func)
        spec = ToolSpec(name=name, description=description, func=func, parameters=parameters)
        self._tools[name] = spec
        return spec

    def get(self, name: str) -> ToolSpec | None:
        """Look up a tool by name."""
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def to_langchain_tools(self) -> list[dict[str, Any]]:
        """Convert all tools to LangChain bind format."""
        return [spec.to_langchain() for spec in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name. Raises KeyError if not found."""
        spec = self._tools.get(name)
        if spec is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        return spec.execute(arguments)

    def _infer_parameters(self, func: Callable[..., Any]) -> dict[str, Any]:
        """Infer a JSON schema from the function signature."""
        sig = inspect.signature(func)
        hints = get_type_hints(func) if not isinstance(func, type) else {}

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
        }

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = hints.get(param_name, str)
            json_type = type_map.get(param_type, "string")
            properties[param_name] = {"type": json_type, "description": ""}
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }
        if required:
            schema["required"] = required
        return schema


# Global default registry for convenience
default_registry = ToolRegistry()


def tool(name: str, description: str, parameters: dict[str, Any] | None = None):
    """Decorator to register a function as a tool in the default registry.

    Usage:
        @tool("read_file", "Read a file's contents", {"type": "object", ...})
        def read_file(path: str) -> str:
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        default_registry.register(name, description, func, parameters)
        return func

    return decorator
