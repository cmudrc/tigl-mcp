"""Lightweight health-check tool for the TiGL MCP server."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tigl_mcp_server.tooling import ToolDefinition, ToolParameters


class PingParams(ToolParameters):
    """Request payload for the ping tool."""

    message: str | None = None


def ping_tool(_session_manager: Any = None) -> ToolDefinition:
    """Build a ping tool definition (session_manager is accepted but unused)."""

    def handler(params: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        reply = params.get("message") or "pong"
        return {
            "ok": True,
            "message": reply,
            "server": "tigl-mcp",
            "timestamp": now,
        }

    return ToolDefinition(
        name="ping",
        description="Lightweight health check that confirms the server is reachable without requiring a CPACS session or TiGL runtime.",
        parameters_model=PingParams,
        handler=handler,
        output_schema={
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "message": {"type": "string"},
                "server": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
            },
            "required": ["ok", "message", "server", "timestamp"],
        },
    )
