"""Model Context Protocol server for TiGL/CPACS geometry."""

from tigl_mcp_server.errors import MCPError
from tigl_mcp_server.session_manager import SessionManager, session_manager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters

__all__ = [
    "MCPError",
    "SessionManager",
    "ToolDefinition",
    "ToolParameters",
    "session_manager",
]
