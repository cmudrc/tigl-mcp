"""Minimal MCP server scaffolding.

This module contains the foundation needed to bootstrap a Model Context Protocol (MCP)
server for TiGL. The current implementation focuses on predictable registration and
execution behavior while leaving network plumbing for future iterations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from tigl_mcp.tools import ToolDefinition


@dataclass
class ToolResult:
    """Result returned by tool execution.

    Attributes:
        name: Name of the tool that produced the result.
        payload: Structured payload returned by the tool.

    """

    name: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        """Serialize the result to JSON.

        Returns:
            JSON representation of the tool result.

        """
        return json.dumps({"name": self.name, "payload": self.payload})


class MCPServer:
    """In-memory registry and dispatcher for MCP tools.

    The server tracks registered tools and provides a simple dispatch mechanism. It is
    intentionally free of transport details to keep the early scaffold focused and
    testable.
    """

    def __init__(self) -> None:
        """Initialize an empty server registry."""
        self._tools: dict[str, ToolDefinition] = {}

    def register_tool(self, tool: ToolDefinition) -> None:
        """Register a tool with the server.

        Args:
            tool: Tool definition to register.

        Raises:
            ValueError: If a tool with the same name is already registered.

        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def available_tools(self) -> list[str]:
        """List the names of registered tools.

        Returns:
            Sorted list of tool names.

        """
        return sorted(self._tools)

    def run_tool(
        self, name: str, *, parameters: dict[str, Any] | None = None
    ) -> ToolResult:
        """Execute a registered tool.

        Args:
            name: Name of the registered tool to execute.
            parameters: Optional parameters for the tool.

        Raises:
            KeyError: If the tool name is not registered.
            ValueError: If parameter validation fails.

        Returns:
            ToolResult containing the tool name and structured payload.

        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")

        tool = self._tools[name]
        validated_params = tool.validate(parameters or {})
        payload = tool.handler(validated_params)
        return ToolResult(name=name, payload=payload)

    def register_tools(self, *tools: ToolDefinition) -> None:
        """Register multiple tools at once.

        Args:
            *tools: Collection of tool definitions to register.

        """
        for tool in tools:
            self.register_tool(tool)

    def to_catalog(self) -> dict[str, dict[str, Any]]:
        """Produce a catalog for discovery.

        Returns:
            Mapping of tool names to their metadata.

        """
        return {name: tool.metadata() for name, tool in self._tools.items()}
