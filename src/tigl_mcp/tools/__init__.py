"""Tool registration helpers for the TiGL MCP server."""

from __future__ import annotations

from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition
from tigl_mcp.tools.checks import check_geometry_tool
from tigl_mcp.tools.configuration import (
    get_component_metadata_tool,
    get_configuration_summary_tool,
    list_geometric_components_tool,
)
from tigl_mcp.tools.cpacs_io import close_cpacs_tool, open_cpacs_tool
from tigl_mcp.tools.export import (
    export_component_mesh_tool,
    export_configuration_cad_tool,
)
from tigl_mcp.tools.parameters import (
    get_high_level_parameters_tool,
    set_high_level_parameters_tool,
)
from tigl_mcp.tools.ping import ping_tool


def build_tools(session_manager: SessionManager) -> list[ToolDefinition]:
    """Instantiate all tool definitions with the provided session manager.

    Removed 2026-10-22: get_wing_summary, get_fuselage_summary,
    sample_component_surface, intersect_with_plane and intersect_components.
    They could only refuse (no host has the native TiGL kernel; the real
    geometry runs in Docker through check_geometry and the exports), and
    every participant of the 2026-10-20 pilot saw that refusal as an error.
    Spans, areas and bounding boxes come from check_geometry.
    """
    return [
        ping_tool(session_manager),
        open_cpacs_tool(session_manager),
        close_cpacs_tool(session_manager),
        get_configuration_summary_tool(session_manager),
        check_geometry_tool(session_manager),
        list_geometric_components_tool(session_manager),
        get_component_metadata_tool(session_manager),
        export_component_mesh_tool(session_manager),
        export_configuration_cad_tool(session_manager),
        get_high_level_parameters_tool(session_manager),
        set_high_level_parameters_tool(session_manager),
    ]
