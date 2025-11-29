"""End-to-end coverage for the FastMCP server wrapper."""

from __future__ import annotations

import pytest
from fastmcp.client import Client

from tigl_mcp_server.fastmcp_adapter import build_fastmcp_app
from tigl_mcp_server.session_manager import SessionManager


@pytest.mark.anyio()
async def test_fastmcp_server_supports_tool_discovery(sample_cpacs_xml: str) -> None:
    """The FastMCP server exposes the TiGL toolset via the official protocol."""
    app, _ = build_fastmcp_app(SessionManager())

    async with Client(app) as client:
        tools = await client.list_tools()
        tool_names = {tool.name for tool in tools}

        assert "open_cpacs" in tool_names
        assert "get_configuration_summary" in tool_names

        open_result = await client.call_tool(
            "open_cpacs", {"source_type": "xml_string", "source": sample_cpacs_xml}
        )
        session_id = open_result.data["session_id"]

        summary = await client.call_tool(
            "get_configuration_summary", {"session_id": session_id}
        )
        assert summary.data["wings"][0]["uid"] == "W1"
        assert summary.data["fuselages"][0]["uid"] == "F1"

        close_result = await client.call_tool("close_cpacs", {"session_id": session_id})
        assert close_result.data["success"] is True


@pytest.mark.anyio()
async def test_fastmcp_propagates_structured_errors() -> None:
    """Errors raised by tool handlers surface through FastMCP client calls."""
    app, _ = build_fastmcp_app(SessionManager())

    async with Client(app) as client:
        result = await client.call_tool(
            "get_configuration_summary",
            {"session_id": "invalid"},
            raise_on_error=False,
        )

    assert result.is_error is True
    assert "Unknown session_id" in result.content[0].text
