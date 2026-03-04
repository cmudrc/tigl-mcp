"""List the current TiGL MCP tools using the in-process FastMCP app."""

from __future__ import annotations

import asyncio
import json

from fastmcp.client import Client

from tigl_mcp.fastmcp_adapter import build_fastmcp_app
from tigl_mcp.session_manager import SessionManager


async def _main() -> None:
    """Run the asynchronous discovery flow and print a stable JSON payload."""
    app, _ = build_fastmcp_app(SessionManager())

    async with Client(app) as client:
        tools = await client.list_tools()

    payload = {
        "tool_count": len(tools),
        "tool_names": sorted(tool.name for tool in tools),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
