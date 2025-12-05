"""Adapters for exposing TiGL MCP tools via FastMCP."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools.tool import ToolResult

from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition
from tigl_mcp_server.tools import build_tools


class ToolDefinitionAdapter(Tool):
    """Expose a :class:`ToolDefinition` as a FastMCP tool."""

    def __init__(self, definition: ToolDefinition) -> None:
        """Create a FastMCP tool wrapper for the provided definition."""
        super().__init__(
            name=definition.name,
            description=definition.description,
            parameters=definition.parameters_model.model_json_schema(),
            output_schema=definition.output_schema,
            tags=set(),
        )
        self._definition = definition

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate arguments and delegate to the wrapped handler."""
        validated_arguments = self._definition.validate(arguments)
        payload = self._definition.handler(validated_arguments)
        return ToolResult(structured_content=payload)


def to_fastmcp_tools(tool_definitions: Sequence[ToolDefinition]) -> list[Tool]:
    """Convert legacy tool definitions into FastMCP-compatible tools."""
    return [ToolDefinitionAdapter(definition) for definition in tool_definitions]


def build_fastmcp_app(
    session_manager: SessionManager,
) -> tuple[FastMCP, list[ToolDefinition]]:
    """Create a FastMCP server instance with all TiGL tools registered."""
    app = FastMCP(
        name="tigl-mcp-server",
        instructions=("CPACS/TiGL utilities exposed over the Model Context Protocol."),
    )
    tool_definitions = build_tools(session_manager)
    for tool in to_fastmcp_tools(tool_definitions):
        app.add_tool(tool)
    return app, tool_definitions
