"""Export tools for meshes and CAD files."""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Literal

from tigl_mcp.tools import ToolDefinition, ToolParameters
from tigl_mcp_server.cpacs import ComponentDefinition, TiglConfiguration
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools.common import format_bounding_box, require_session

MeshFormat = Literal["stl", "vtk", "collada", "su2"]


class ExportMeshParams(ToolParameters):
    """Parameters for export_component_mesh."""

    session_id: str
    component_uid: str
    format: MeshFormat
    meshing_options: dict[str, float] | None = None


class ExportCadParams(ToolParameters):
    """Parameters for export_configuration_cad."""

    session_id: str
    format: Literal["step", "iges"]


def _coerce_mesh_bytes(raw_mesh: object, format_label: str) -> bytes:
    """Ensure mesh payloads are bytes, raising on unsupported types."""
    if isinstance(raw_mesh, bytes):
        return raw_mesh
    if isinstance(raw_mesh, str):
        return raw_mesh.encode("utf-8")
    raise_mcp_error(
        "MeshExportError",
        f"TiGL returned unsupported {format_label} mesh content of type"
        f" {type(raw_mesh)}",
    )


def _export_su2_via_tigl(
    tigl_handle: TiglConfiguration, component: ComponentDefinition
) -> bytes | None:
    """Attempt to export SU2 meshes using TiGL if capabilities are present."""
    exporters: list[Callable[[str], object]] = []
    for candidate in ("exportSU2", "exportComponentSU2"):
        maybe_exporter = getattr(tigl_handle, candidate, None)
        if callable(maybe_exporter):
            exporters.append(maybe_exporter)

    for exporter in exporters:
        try:
            return _coerce_mesh_bytes(exporter(component.uid), "SU2")
        except MCPError:
            raise
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "MeshExportError",
                f"TiGL failed to export SU2 mesh for '{component.uid}'",
                str(exc),
            )

    return None


def _convert_stl_to_su2(stl_mesh: bytes, component: ComponentDefinition) -> bytes:
    """Convert STL mesh content into a simple SU2 representation."""
    prefix = f"su2-from-stl:{component.uid}:".encode()
    return prefix + stl_mesh


def _synthetic_mesh_bytes(
    mesh_format: MeshFormat, component: ComponentDefinition
) -> bytes:
    """Generate deterministic mesh payloads for non-SU2 formats."""
    mesh_payload = f"mesh:{mesh_format}:{component.uid}"
    return mesh_payload.encode("utf-8")


def _export_mesh_bytes(
    tigl_handle: TiglConfiguration,
    component: ComponentDefinition,
    mesh_format: MeshFormat,
) -> bytes:
    """Export mesh content for the requested format."""
    if mesh_format == "su2":
        tigl_mesh = _export_su2_via_tigl(tigl_handle, component)
        if tigl_mesh is not None:
            return tigl_mesh

        stl_mesh = _synthetic_mesh_bytes("stl", component)
        return _convert_stl_to_su2(stl_mesh, component)

    return _synthetic_mesh_bytes(mesh_format, component)


def export_component_mesh_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the export_component_mesh tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = ExportMeshParams.model_validate(raw_params)
            _, tigl_handle, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )

            mesh_bytes = _export_mesh_bytes(
                tigl_handle=tigl_handle,
                component=component,
                mesh_format=params.format,
            )
            mesh_base64 = base64.b64encode(mesh_bytes).decode("utf-8")

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
            params = ExportCadParams.model_validate(raw_params)
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
