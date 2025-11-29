"""tigl_mcp package initialization."""

from tigl_mcp.server import MCPServer
from tigl_mcp.tools import ToolDefinition, register_dummy_tool

__all__ = ["MCPServer", "ToolDefinition", "register_dummy_tool"]
