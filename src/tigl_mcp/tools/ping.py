"""Lightweight health-check tool for the TiGL MCP server."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from tigl_mcp.tooling import ToolDefinition, ToolParameters

if TYPE_CHECKING:
    from tigl_mcp.session_manager import SessionManager


class PingParams(ToolParameters):
    """Request payload for the ping tool."""

    message: str | None = None


def ping_tool(
    _session_manager: SessionManager,
) -> ToolDefinition:
    """Build a ping tool definition."""

    def handler(params: dict[str, object]) -> dict[str, object]:
        now = datetime.now(UTC).isoformat()
        reply = params.get("message") or "pong"
        return {
            "ok": True,
            "message": reply,
            "server": "tigl-mcp",
            "timestamp": now,
        }

    _ping_desc = (
        "Lightweight health check that confirms the server"
        " is reachable without requiring a CPACS session"
        " or TiGL runtime."
    )

    return ToolDefinition(
        name="ping",
        description=_ping_desc,
        parameters_model=PingParams,
        handler=handler,
        output_schema={
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "message": {"type": "string"},
                "server": {"type": "string"},
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                },
            },
            "required": [
                "ok",
                "message",
                "server",
                "timestamp",
            ],
        },
    )
