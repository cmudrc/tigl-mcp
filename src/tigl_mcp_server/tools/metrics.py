"""Tools that compute simplified geometric metrics."""

from __future__ import annotations

from tigl_mcp_server.cpacs import ComponentDefinition, CPACSConfiguration
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters
from tigl_mcp_server.tools.common import require_session


class WingSummaryParams(ToolParameters):
    """Parameters for get_wing_summary."""

    session_id: str
    wing_uid: str


class FuselageSummaryParams(ToolParameters):
    """Parameters for get_fuselage_summary."""

    session_id: str
    fuselage_uid: str


def _safe_get_component(
    config: CPACSConfiguration, uid: str, type_name: str
) -> ComponentDefinition:
    """Resolve a component or raise an MCP error."""
    component = config.find_component(uid)
    if component is None:
        raise_mcp_error("NotFound", f"{type_name} '{uid}' not found")
    return component


def get_wing_summary_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the get_wing_summary tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = WingSummaryParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = _safe_get_component(config, params.wing_uid, "Wing")
            span = component.parameters.get("span", 20.0 + component.index)
            reference_area = component.parameters.get("area", span * 0.8)
            half_span = span / 2.0
            top_area = reference_area * 0.5 if reference_area else None
            aspect_ratio = (span**2) / reference_area if reference_area else None
            mac_length = component.parameters.get("mac_length")
            sweep = component.parameters.get("sweep")
            dihedral = component.parameters.get("dihedral")
            mac_quarter_chord = {
                "x": component.bounding_box.xmin
                + 0.25 * (component.bounding_box.xmax - component.bounding_box.xmin),
                "y": component.bounding_box.ymin
                + 0.25 * (component.bounding_box.ymax - component.bounding_box.ymin),
                "z": component.bounding_box.zmin
                + 0.25 * (component.bounding_box.zmax - component.bounding_box.zmin),
            }
            return {
                "span": span,
                "half_span": half_span,
                "reference_area": reference_area,
                "wetted_area": component.parameters.get("wetted_area"),
                "top_area": top_area,
                "aspect_ratio": aspect_ratio,
                "mac_length": mac_length,
                "mac_quarter_chord": mac_quarter_chord,
                "sweep_deg": sweep,
                "dihedral_deg": dihedral,
                "symmetry": component.symmetry,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "WingSummaryError", "Failed to compute wing summary", str(exc)
            )

    return ToolDefinition(
        name="get_wing_summary",
        description="Return key geometric metrics for a wing.",
        parameters_model=WingSummaryParams,
        handler=handler,
        output_schema={},
    )


def get_fuselage_summary_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the get_fuselage_summary tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = FuselageSummaryParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = _safe_get_component(config, params.fuselage_uid, "Fuselage")
            length = component.parameters.get("length", 15.0 + component.index)
            wetted_area = component.parameters.get("wetted_area")
            max_cross_section_area = component.parameters.get("max_cross_section_area")
            max_diameter = component.parameters.get("max_diameter")
            approx_volume = component.parameters.get("volume")
            return {
                "length": length,
                "wetted_area": wetted_area,
                "max_cross_section_area": max_cross_section_area,
                "max_diameter": max_diameter,
                "approx_volume": approx_volume,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "FuselageSummaryError", "Failed to compute fuselage summary", str(exc)
            )

    return ToolDefinition(
        name="get_fuselage_summary",
        description="Return key geometric metrics for a fuselage.",
        parameters_model=FuselageSummaryParams,
        handler=handler,
        output_schema={},
    )
