"""FastMCP integration coverage for the tool runtime."""

from __future__ import annotations

import base64

import pytest
from fastmcp.client import Client
from fastmcp.exceptions import ToolError

from tigl_mcp import cpacs_adapter
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
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FastMCP clients see real counts, and errors where a kernel is needed."""
    real_stl = (
        b"solid W1\n"
        b"  facet normal 0 0 1\n"
        b"    outer loop\n"
        b"      vertex 12.744 0.0 0.0\n"
        b"      vertex 22.137 0.0 0.0\n"
        b"      vertex 17.0 16.963 0.0\n"
        b"    endloop\n"
        b"  endfacet\n"
        b"endsolid W1\n"
    )
    # Minimal IGES-shaped payload: 72 columns of content then the S-section
    # sequence marker, which is what the format's first record looks like.
    real_iges = b" " * 72 + b"S      1\n"
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_mesh_via_docker", lambda *a, **k: real_stl
    )
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_cad_via_docker", lambda *a, **k: real_iges
    )
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

        # Exports route to real TiGL. The kernel is stubbed out here so the
        # test is deterministic on hosts with and without Docker; what is
        # asserted is that the tool returns the kernel's bytes unaltered.
        mesh_export = await client.call_tool(
            "export_component_mesh",
            {
                "session_id": session_id,
                "component_uid": "W1",
                "format": "stl",
            },
        )
        assert base64.b64decode(mesh_export.data["mesh_base64"]) == real_stl

        cad_export = await client.call_tool(
            "export_configuration_cad", {"session_id": session_id, "format": "iges"}
        )
        cpacs_text = base64.b64decode(cad_export.data["cpacs_xml_base64"]).decode()
        assert base64.b64decode(cad_export.data["cad_base64"]) == real_iges
        assert cad_export.data["source"] == "docker_tigl"
        assert "<cpacs>" in cpacs_text
