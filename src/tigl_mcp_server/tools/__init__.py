"""Tool registration helpers for the TiGL MCP server."""

from __future__ import annotations

from tigl_mcp.tools import ToolDefinition
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools.configuration import (
    get_component_metadata_tool,
    get_configuration_summary_tool,
    list_geometric_components_tool,
)
from tigl_mcp_server.tools.cpacs_io import close_cpacs_tool, open_cpacs_tool
from tigl_mcp_server.tools.export import (
    export_component_mesh_tool,
    export_configuration_cad_tool,
)
from tigl_mcp_server.tools.metrics import (
    get_fuselage_summary_tool,
    get_wing_summary_tool,
)
from tigl_mcp_server.tools.parameters import (
    get_high_level_parameters_tool,
    set_high_level_parameters_tool,
)
from tigl_mcp_server.tools.sampling import (
    intersect_components_tool,
    intersect_with_plane_tool,
    sample_component_surface_tool,
)


def build_tools(session_manager: SessionManager) -> list[ToolDefinition]:
    """Instantiate all tool definitions with the provided session manager."""
    return [
        open_cpacs_tool(session_manager),
        close_cpacs_tool(session_manager),
        get_configuration_summary_tool(session_manager),
        list_geometric_components_tool(session_manager),
        get_component_metadata_tool(session_manager),
        get_wing_summary_tool(session_manager),
        get_fuselage_summary_tool(session_manager),
        sample_component_surface_tool(session_manager),
        intersect_with_plane_tool(session_manager),
        intersect_components_tool(session_manager),
        export_component_mesh_tool(session_manager),
        export_configuration_cad_tool(session_manager),
        get_high_level_parameters_tool(session_manager),
        set_high_level_parameters_tool(session_manager),
    ]
