"""Surface sampling and intersection tools.

Sampling a point on a component surface, or intersecting a component with a
plane or another component, are boundary-representation operations. They need
the actual lofted surfaces that TiGL builds from the CPACS profiles; the XML
alone cannot answer them. Until a real TiGL kernel is wired in, these tools
raise a structured ``GeometryUnavailable`` error rather than returning points
that lie on nothing, per the project's no-stubs rule.
"""

from __future__ import annotations

from typing import Literal

from tigl_mcp.errors import MCPError, raise_mcp_error
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition, ToolParameters
from tigl_mcp.tools.common import require_session

#: Guidance returned with every GeometryUnavailable error.
_TIGL_REQUIRED = (
    "This operation requires a real TiGL kernel. Native bindings (tigl3/tixi3) "
    "are not importable in this environment. Install TiGL "
    "(https://github.com/DLR-SC/tigl), or use export_configuration_cad, which "
    "runs real TiGL via the tigl-mcp:dev Docker image and returns STEP "
    "geometry you can intersect or sample downstream."
)


class SampleSurfaceParams(ToolParameters):
    """Parameters for sample_component_surface."""

    session_id: str
    component_uid: str
    parameterization: Literal[
        "wing_component_segment_eta_xsi",
        "wing_segment_eta_xsi",
        "fuselage_segment_eta_xsi",
    ]
    samples: list[dict[str, float | int | str | None]]


class IntersectPlaneParams(ToolParameters):
    """Parameters for intersect_with_plane."""

    session_id: str
    component_uid: str
    plane_point: dict[str, float]
    plane_normal: dict[str, float]
    n_points_per_curve: int = 50


class IntersectComponentsParams(ToolParameters):
    """Parameters for intersect_components."""

    session_id: str
    component_uid_one: str
    component_uid_two: str
    n_points_per_curve: int = 50


def sample_component_surface_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the sample_component_surface tool."""

    def handler(
        raw_params: dict[str, object],
    ) -> dict[str, list[dict[str, float | str | None]]]:
        try:
            params = SampleSurfaceParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )
            raise_mcp_error(
                "GeometryUnavailable",
                f"Cannot sample the surface of '{component.uid}' without a real "
                "geometry kernel.",
                _TIGL_REQUIRED,
            )
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("SampleError", "Failed to sample surface", str(exc))

    return ToolDefinition(
        name="sample_component_surface",
        description="Sample 3D points on a component surface.",
        parameters_model=SampleSurfaceParams,
        handler=handler,
        output_schema={},
    )


def intersect_with_plane_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the intersect_with_plane tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, list[dict[str, object]]]:
        try:
            params = IntersectPlaneParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )
            raise_mcp_error(
                "GeometryUnavailable",
                f"Cannot intersect '{component.uid}' with a plane without a real "
                "geometry kernel.",
                _TIGL_REQUIRED,
            )
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "IntersectionError", "Failed to intersect with plane", str(exc)
            )

    return ToolDefinition(
        name="intersect_with_plane",
        description="Intersect a component with a plane and sample polylines.",
        parameters_model=IntersectPlaneParams,
        handler=handler,
        output_schema={},
    )


def intersect_components_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the intersect_components tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, list[dict[str, object]]]:
        try:
            params = IntersectComponentsParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            first = config.find_component(params.component_uid_one)
            second = config.find_component(params.component_uid_two)
            if first is None or second is None:
                raise_mcp_error(
                    "NotFound", "One or both components could not be located"
                )
            raise_mcp_error(
                "GeometryUnavailable",
                f"Cannot intersect '{first.uid}' with '{second.uid}' without a "
                "real geometry kernel.",
                _TIGL_REQUIRED,
            )
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "IntersectionError", "Failed to intersect components", str(exc)
            )

    return ToolDefinition(
        name="intersect_components",
        description="Intersect two components and return sampled curves.",
        parameters_model=IntersectComponentsParams,
        handler=handler,
        output_schema={},
    )
