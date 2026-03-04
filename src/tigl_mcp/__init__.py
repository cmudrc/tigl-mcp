"""Model Context Protocol server for TiGL/CPACS geometry."""

from tigl_mcp.errors import MCPError
from tigl_mcp.session_manager import SessionManager, session_manager
from tigl_mcp.tooling import ToolDefinition, ToolParameters

__all__ = [
    "MCPError",
    "SessionManager",
    "ToolDefinition",
    "ToolParameters",
    "session_manager",
]
