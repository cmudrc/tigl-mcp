"""Tools that report geometric metrics for CPACS components.

Span, area, aspect ratio, MAC, and fuselage length cannot be read out of CPACS
XML. They are results of evaluating the profile geometry through the
positioning and transformation chain, which is TiGL's job. Until a real TiGL
kernel is wired in, these tools raise a structured ``GeometryUnavailable``
error rather than returning an approximation, per the project's no-stubs rule.
"""

from __future__ import annotations

from tigl_mcp.cpacs import ComponentDefinition, CPACSConfiguration
from tigl_mcp.errors import MCPError, raise_mcp_error
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition, ToolParameters
from tigl_mcp.tools.common import require_session

#: Guidance returned with every GeometryUnavailable error.
_TIGL_REQUIRED = (
    "This value requires a real TiGL kernel. Native bindings (tigl3/tixi3) are "
    "not importable in this environment. Install TiGL "
    "(https://github.com/DLR-SC/tigl), or use export_configuration_cad, which "
    "runs real TiGL via the tigl-mcp:dev Docker image and returns STEP "
    "geometry you can measure."
)


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
            # Resolve first, so an unknown UID still reports NotFound.
            component = _safe_get_component(config, params.wing_uid, "Wing")
            raise_mcp_error(
                "GeometryUnavailable",
                f"Cannot compute wing metrics for '{component.uid}' without a "
                "real geometry kernel.",
                _TIGL_REQUIRED,
            )
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
            raise_mcp_error(
                "GeometryUnavailable",
                f"Cannot compute fuselage metrics for '{component.uid}' without "
                "a real geometry kernel.",
                _TIGL_REQUIRED,
            )
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
