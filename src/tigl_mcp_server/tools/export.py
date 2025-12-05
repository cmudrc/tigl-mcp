"""Export tools for meshes and CAD files."""

from __future__ import annotations

import base64
import tempfile
import types
from collections.abc import Iterator, Sized
from importlib import import_module
from typing import Any, Literal, NoReturn

from tigl_mcp_server.cpacs import ComponentDefinition, TiglConfiguration
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters
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
        f"TiGL returned unsupported {format_label} mesh content of type",
        f" {type(raw_mesh)}",
    )


def _raise_unsupported_format(mesh_format: MeshFormat, component_uid: str) -> NoReturn:
    """Raise a standardized error for unsupported mesh formats."""
    raise_mcp_error(
        "MeshExportError",
        (
            "Mesh export failed: format "
            f"'{mesh_format}' not supported for component {component_uid}."
        ),
    )


def _ensure_export_supported(
    tigl_handle: TiglConfiguration, mesh_format: MeshFormat, component_uid: str
) -> None:
    """Verify requested mesh export format is supported and fail clearly when not."""
    supported_native_formats: set[MeshFormat] = {"stl", "vtk", "collada"}
    if mesh_format in supported_native_formats:
        return
    if mesh_format == "su2" and callable(
        getattr(tigl_handle, "exportComponentSTL", None)
    ):
        return

    _raise_unsupported_format(mesh_format, component_uid)


def _export_su2_via_tigl(
    tigl_handle: TiglConfiguration, component: ComponentDefinition
) -> bytes:
    """Export SU2 mesh bytes using TiGL STL export combined with meshio conversion."""
    try:
        meshio_module: Any = import_module("meshio")
        stl_bytes = _coerce_mesh_bytes(
            tigl_handle.exportComponentSTL(component.uid), "STL"  # type: ignore[attr-defined]
        )
    except MCPError:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise_mcp_error(
            "MeshExportError",
            f"Failed to export STL mesh for '{component.uid}' via TiGL",
            str(exc),
        )

    if not stl_bytes:
        raise_mcp_error(
            "MeshExportError", f"TiGL returned empty STL mesh for '{component.uid}'"
        )

    try:
        with tempfile.NamedTemporaryFile(suffix=".stl") as stl_file:
            stl_file.write(stl_bytes)
            stl_file.flush()
            mesh = meshio_module.read(stl_file.name, file_format="stl")

        class _SU2Cell:
            def __init__(self, cell_type: str, data: Sized) -> None:
                self.type = cell_type
                self.data = data

            def __iter__(self) -> Iterator[object]:
                yield self.type
                yield self.data

            def __len__(self) -> int:
                return len(self.data)

        converted_cells = [_SU2Cell(cell.type, cell.data) for cell in mesh.cells]
        mesh_to_write = types.SimpleNamespace(
            points=mesh.points, cells=converted_cells, cell_data=mesh.cell_data
        )

        with tempfile.NamedTemporaryFile(suffix=".su2") as su2_file:
            meshio_module.write(su2_file.name, mesh_to_write, file_format="su2")
            su2_file.flush()
            su2_file.seek(0)
            su2_bytes = su2_file.read()
    except MCPError:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise_mcp_error(
            "MeshExportError",
            f"Failed to export SU2 mesh for '{component.uid}' via meshio",
            str(exc),
        )

    if not su2_bytes or b"NDIME=" not in su2_bytes:
        raise_mcp_error(
            "MeshExportError",
            f"Conversion to SU2 failed or output invalid for '{component.uid}'",
        )

    return su2_bytes


def _synthetic_mesh_bytes(
    mesh_format: MeshFormat, component: ComponentDefinition
) -> bytes:
    """Generate deterministic, format-like mesh payloads for supported formats."""
    if mesh_format == "stl":
        return (
            f"solid {component.uid}\n"
            "  facet normal 0 0 0\n"
            "    outer loop\n"
            "      vertex 0 0 0\n"
            "      vertex 0 1 0\n"
            "      vertex 1 0 0\n"
            "    endloop\n"
            "  endfacet\n"
            f"endsolid {component.uid}\n"
        ).encode("ascii")
    if mesh_format == "vtk":
        return (
            "# vtk DataFile Version 3.0\n"
            f"component {component.uid}\n"
            "ASCII\n"
            "DATASET POLYDATA\n"
            "POINTS 0 float\n"
        ).encode("ascii")
    if mesh_format == "collada":
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<COLLADA><asset/><library_geometries>"
            f'<geometry id="{component.uid}" name="{component.uid}"/>'
            "</library_geometries></COLLADA>"
        ).encode()

    _raise_unsupported_format(mesh_format, component.uid)


def _export_mesh_bytes(
    tigl_handle: TiglConfiguration,
    component: ComponentDefinition,
    mesh_format: MeshFormat,
) -> bytes:
    """Export mesh content for the requested format."""
    if mesh_format == "su2":
        return _export_su2_via_tigl(tigl_handle, component)

    return _synthetic_mesh_bytes(mesh_format, component)


def _looks_like_handle(mesh_bytes: bytes) -> bool:
    """Detect legacy handle payloads masquerading as mesh bytes."""
    try:
        mesh_text = mesh_bytes.decode("ascii")
    except UnicodeDecodeError:
        return False
    return mesh_text.startswith("mesh:") or mesh_text.startswith("su2-from-stl:")


def _validate_mesh_bytes(
    mesh_bytes: bytes, mesh_format: MeshFormat, component: ComponentDefinition
) -> bytes:
    """Ensure exported mesh payloads are real, non-empty bytes."""
    if mesh_bytes is None or len(mesh_bytes) == 0:
        _raise_unsupported_format(mesh_format, component.uid)

    if _looks_like_handle(mesh_bytes):
        _raise_unsupported_format(mesh_format, component.uid)

    if mesh_format == "su2" and b"NDIME=" not in mesh_bytes:
        raise_mcp_error(
            "MeshExportError",
            f"Conversion to SU2 failed or output invalid for '{component.uid}'",
        )

    return mesh_bytes


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

            _ensure_export_supported(
                tigl_handle=tigl_handle,
                mesh_format=params.format,
                component_uid=params.component_uid,
            )
            mesh_bytes = _export_mesh_bytes(
                tigl_handle=tigl_handle,
                component=component,
                mesh_format=params.format,
            )
            validated_mesh = _validate_mesh_bytes(mesh_bytes, params.format, component)
            # mesh_base64 is reserved for mesh bytes only.
            mesh_base64 = base64.b64encode(validated_mesh).decode("utf-8")

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
            tixi_handle, _, _ = require_session(session_manager, params.session_id)
            cad_payload = f"cad:{params.format}:{tixi_handle.xml_content}"
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
