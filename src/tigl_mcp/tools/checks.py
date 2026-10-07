"""Geometry consistency check: the lofts real TiGL built against the file.

Catches the faults a multimodal observer missed on the rendered flow field
(2026-10-05): a wing on one side only, a wing not touching the fuselage, a
reference area that cannot belong to the wing it is stated for, and a
component the fused export left out. It needs the containerised TiGL runtime;
without it the tool reports GeometryUnavailable rather than guessing.
"""

from __future__ import annotations

from tigl_mcp import cpacs_adapter
from tigl_mcp.errors import MCPError, raise_mcp_error
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition, ToolParameters
from tigl_mcp.tools.common import require_session


class CheckGeometryParams(ToolParameters):
    """Parameters for check_geometry."""

    session_id: str


def check_geometry_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the check_geometry tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = CheckGeometryParams.model_validate(raw_params)
            require_session(session_manager, params.session_id)
            cpacs_xml = session_manager.get_cpacs_xml(params.session_id)
            results = cpacs_adapter.read_from_cpacs(cpacs_xml)
            cpacs_adapter._merge_docker_geometry(cpacs_xml, results)
            check = results.get("geometry_check")
            if not isinstance(check, dict) or not check.get("checked"):
                raise_mcp_error(
                    "GeometryUnavailable",
                    "The geometry could not be checked: no TiGL kernel supplied "
                    "bounding boxes or planform areas.",
                    "Start Docker with the tigl-mcp:dev image, or install native "
                    "tigl3/tixi3, then call check_geometry again.",
                )
            components = [
                {
                    k: c.get(k)
                    for k in (
                        "uid",
                        "type",
                        "tigl_symmetry",
                        "tigl_reference_area_m2",
                        "bounding_box",
                        "min_distance_to_fuselage_m",
                    )
                    if c.get(k) is not None
                }
                for c in results.get("components", [])
            ]
            return {
                "geometry_check": check,
                "ref_area_m2": results.get("ref_area_m2"),
                "components": components,
                "geometry_source": results.get("geometry_source"),
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("CheckGeometryError", "Failed to check geometry", str(exc))

    return ToolDefinition(
        name="check_geometry",
        description=(
            "Check the aircraft's geometry, as real TiGL builds it, against the "
            "file: a wing on one side only, a wing not touching the fuselage, a "
            "reference area that cannot belong to the largest wing. Returns the "
            "findings (each with severity 'fault', the component, what was "
            "measured and the tolerance) and the per-component bounding boxes. "
            "Run it after opening a file and before meshing."
        ),
        parameters_model=CheckGeometryParams,
        handler=handler,
        output_schema={},
    )
