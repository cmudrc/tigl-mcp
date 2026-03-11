"""Tests for the lightweight ping tool."""

from __future__ import annotations

from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition
from tigl_mcp_server.tools import build_tools
from tigl_mcp_server.tools.ping import ping_tool


def test_ping_tool_is_registered() -> None:
    """The ping tool should be present in the build_tools list."""
    manager = SessionManager()
    tools = build_tools(manager)
    names = [t.name for t in tools]
    assert "ping" in names


def test_ping_returns_pong_by_default() -> None:
    """Calling ping with no message should return 'pong'."""
    tool = ping_tool()
    result = tool.handler(tool.validate({}))
    assert result["ok"] is True
    assert result["message"] == "pong"
    assert result["server"] == "tigl-mcp"
    assert "timestamp" in result


def test_ping_echoes_custom_message() -> None:
    """Calling ping with a message should echo it back."""
    tool = ping_tool()
    result = tool.handler(tool.validate({"message": "hello"}))
    assert result["message"] == "hello"


def test_ping_tool_metadata() -> None:
    """The tool should expose proper discovery metadata."""
    tool = ping_tool()
    meta = tool.metadata()
    assert meta["name"] == "ping"
    assert "health" in meta["description"].lower() or "ping" in meta["description"].lower()
