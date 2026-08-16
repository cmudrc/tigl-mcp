"""FastMCP integration coverage for the tool runtime."""

from __future__ import annotations

import base64

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from tigl_mcp.fastmcp_adapter import build_fastmcp_app
from tigl_mcp.session_manager import SessionManager


@pytest.mark.anyio()
async def test_fastmcp_server_supports_tool_discovery(sample_cpacs_xml: str) -> None:
    """The FastMCP surface exposes the current TiGL tool catalog."""
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
    """Structured tool errors remain visible through the FastMCP client surface."""
    app, _ = build_fastmcp_app(SessionManager())

    async with Client(app) as client:
        result = await client.call_tool(
            "get_configuration_summary",
            {"session_id": "invalid"},
            raise_on_error=False,
        )

    assert result.is_error is True
    assert "Unknown session_id" in result.content[0].text


@pytest.mark.anyio()
async def test_fastmcp_server_exposes_export_endpoints(
    sample_cpacs_xml: str,
) -> None:
    """FastMCP clients see real counts, and errors where a kernel is needed."""
    app, _ = build_fastmcp_app(SessionManager())

    async with Client(app) as client:
        open_result = await client.call_tool(
            "open_cpacs", {"source_type": "xml_string", "source": sample_cpacs_xml}
        )
        session_id = open_result.data["session_id"]

        components = await client.call_tool(
            "list_geometric_components", {"session_id": session_id}
        )
        assert {component["uid"] for component in components.data["components"]} == {
            "W1",
            "F1",
        }

        wing_metadata = await client.call_tool(
            "get_component_metadata",
            {"session_id": session_id, "component_uid": "W1"},
        )
        # Counts are parsed from the file, so they reflect the fixture.
        assert wing_metadata.data["wing_data"]["num_sections"] == 3
        assert wing_metadata.data["wing_data"]["num_segments"] == 2
        assert wing_metadata.data["bounding_box"] is None

        # Metrics need a real kernel, so over MCP they surface as tool errors
        # rather than plausible-looking numbers.
        for tool_name, payload in (
            ("get_wing_summary", {"session_id": session_id, "wing_uid": "W1"}),
            (
                "get_fuselage_summary",
                {"session_id": session_id, "fuselage_uid": "F1"},
            ),
        ):
            with pytest.raises(ToolError, match="without a real geometry kernel"):
                await client.call_tool(tool_name, payload)

        mesh_export = await client.call_tool(
            "export_component_mesh",
            {
                "session_id": session_id,
                "component_uid": "W1",
                "format": "stl",
            },
        )
        mesh_bytes = base64.b64decode(mesh_export.data["mesh_base64"])
        assert mesh_bytes.startswith(b"solid W1")

        cad_export = await client.call_tool(
            "export_configuration_cad", {"session_id": session_id, "format": "iges"}
        )
        cad_text = base64.b64decode(cad_export.data["cad_base64"]).decode()
        cpacs_text = base64.b64decode(cad_export.data["cpacs_xml_base64"]).decode()
        assert cad_text.startswith("cad:iges:")
        assert cad_export.data["source"] == "stub"
        assert "<cpacs>" in cad_text
        assert "<cpacs>" in cpacs_text
