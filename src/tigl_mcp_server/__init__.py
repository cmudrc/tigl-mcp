"""Model Context Protocol server for TiGL/CPACS geometry."""

from tigl_mcp_server.errors import MCPError
from tigl_mcp_server.session_manager import SessionManager, session_manager

__all__ = ["MCPError", "SessionManager", "session_manager"]
