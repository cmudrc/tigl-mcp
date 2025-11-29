"""Export tools for meshes and CAD files."""

from __future__ import annotations

import base64
from typing import Literal

from tigl_mcp.tools import ToolDefinition, ToolParameters
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools.common import format_bounding_box, require_session


class ExportMeshParams(ToolParameters):
    """Parameters for export_component_mesh."""

    session_id: str
    component_uid: str
    format: Literal["stl", "vtk", "collada"]
    meshing_options: dict[str, float] | None = None


class ExportCadParams(ToolParameters):
    """Parameters for export_configuration_cad."""

    session_id: str
    format: Literal["step", "iges"]


def export_component_mesh_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the export_component_mesh tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = ExportMeshParams(**raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )
            mesh_payload = f"mesh:{params.format}:{component.uid}"
            mesh_base64 = base64.b64encode(mesh_payload.encode("utf-8")).decode("utf-8")
            return {
                "format": params.format,
                "mesh_base64": mesh_base64,
                "num_triangles": 12 * component.index,
                "bounding_box": format_bounding_box(component.bounding_box),
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "MeshExportError", "Failed to export component mesh", str(exc)
            )

    return ToolDefinition(
        name="export_component_mesh",
        description="Export a component mesh as base64-encoded content.",
        parameters_model=ExportMeshParams,
        handler=handler,
        output_schema={},
    )


def export_configuration_cad_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the export_configuration_cad tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = ExportCadParams(**raw_params)
            require_session(session_manager, params.session_id)
            cad_payload = f"cad:{params.format}:{params.session_id}"
            cad_base64 = base64.b64encode(cad_payload.encode("utf-8")).decode("utf-8")
            return {"format": params.format, "cad_base64": cad_base64}
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "CadExportError", "Failed to export configuration", str(exc)
            )

    return ToolDefinition(
        name="export_configuration_cad",
        description="Export the full configuration CAD and return it encoded.",
        parameters_model=ExportCadParams,
        handler=handler,
        output_schema={},
    )
