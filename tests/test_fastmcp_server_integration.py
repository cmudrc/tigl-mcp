"""End-to-end coverage for the FastMCP server wrapper."""

from __future__ import annotations

import base64

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


@pytest.mark.anyio()
async def test_fastmcp_server_exposes_all_tool_endpoints(
    sample_cpacs_xml: str,
) -> None:
    """Every server endpoint is callable and returns structured data."""
    app, _ = build_fastmcp_app(SessionManager())

    async with Client(app) as client:
        open_result = await client.call_tool(
            "open_cpacs", {"source_type": "xml_string", "source": sample_cpacs_xml}
        )
        session_id = open_result.data["session_id"]

        summary = await client.call_tool(
            "get_configuration_summary", {"session_id": session_id}
        )
        assert summary.data["wings"][0]["uid"] == "W1"
        assert summary.data["fuselages"][0]["uid"] == "F1"

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
        assert wing_metadata.data["wing_data"]["num_segments"] == 0

        wing_summary = await client.call_tool(
            "get_wing_summary", {"session_id": session_id, "wing_uid": "W1"}
        )
        assert wing_summary.data["span"] > 0.0

        fuselage_summary = await client.call_tool(
            "get_fuselage_summary",
            {"session_id": session_id, "fuselage_uid": "F1"},
        )
        assert fuselage_summary.data["length"] > 0.0

        surface_sample = await client.call_tool(
            "sample_component_surface",
            {
                "session_id": session_id,
                "component_uid": "W1",
                "parameterization": "wing_component_segment_eta_xsi",
                "samples": [{"eta": 0.5, "xsi": 0.25, "side": "left"}],
            },
        )
        assert surface_sample.data["points"][0]["x"] != 0

        plane_intersection = await client.call_tool(
            "intersect_with_plane",
            {
                "session_id": session_id,
                "component_uid": "W1",
                "plane_point": {"x": 0.0, "y": 0.0, "z": 0.0},
                "plane_normal": {"nx": 1.0, "ny": 0.0, "nz": 0.0},
                "n_points_per_curve": 3,
            },
        )
        assert len(plane_intersection.data["curves"][0]["points"]) == 3

        component_intersection = await client.call_tool(
            "intersect_components",
            {
                "session_id": session_id,
                "component_uid_one": "W1",
                "component_uid_two": "F1",
                "n_points_per_curve": 4,
            },
        )
        assert len(component_intersection.data["curves"][0]["points"]) == 4

        mesh_export = await client.call_tool(
            "export_component_mesh",
            {
                "session_id": session_id,
                "component_uid": "W1",
                "format": "stl",
            },
        )
        mesh_bytes = base64.b64decode(mesh_export.data["mesh_base64"])
        assert mesh_bytes.startswith(b"mesh:stl")

        cad_export = await client.call_tool(
            "export_configuration_cad", {"session_id": session_id, "format": "iges"}
        )
        cad_text = base64.b64decode(cad_export.data["cad_base64"]).decode()
        assert "<cpacs>" in cad_text

        parameter_values = await client.call_tool(
            "get_high_level_parameters",
            {"session_id": session_id, "component_uid": "W1"},
        )
        assert parameter_values.data["parameters"]["span"] == 30.0

        updated_parameters = await client.call_tool(
            "set_high_level_parameters",
            {
                "session_id": session_id,
                "component_uid": "W1",
                "updates": {"area": 82.0},
            },
        )
        assert updated_parameters.data["new_parameters"]["area"] == 82.0

        close_result = await client.call_tool("close_cpacs", {"session_id": session_id})
        assert close_result.data["success"] is True
