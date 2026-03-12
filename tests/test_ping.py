"""Coverage for the lightweight ping tool."""

from __future__ import annotations

from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tools import build_tools


def test_ping_returns_pong_by_default() -> None:
    """Without a custom message the ping tool echoes 'pong'."""
    tools = build_tools(SessionManager())
    ping = next(t for t in tools if t.name == "ping")

    result = ping.handler({})

    assert result["ok"] is True
    assert result["message"] == "pong"
    assert result["server"] == "tigl-mcp"
    assert "timestamp" in result


def test_ping_echoes_custom_message() -> None:
    """The ping tool echoes back a user-supplied message."""
    tools = build_tools(SessionManager())
    ping = next(t for t in tools if t.name == "ping")

    result = ping.handler({"message": "hello"})

    assert result["message"] == "hello"
