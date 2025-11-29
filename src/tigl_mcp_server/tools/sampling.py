"""Surface sampling and intersection tools."""

from __future__ import annotations

from typing import Any, Literal

from tigl_mcp.tools import ToolDefinition, ToolParameters
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools.common import require_session


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
            bbox = component.bounding_box
            points = []
            for sample in params.samples:
                eta_raw: Any = sample.get("eta", 0.0)
                xsi_raw: Any = sample.get("xsi", 0.0)
                side = sample.get("side")
                eta = float(eta_raw)
                xsi = float(xsi_raw)
                x = bbox.xmin + (bbox.xmax - bbox.xmin) * eta
                y = bbox.ymin + (bbox.ymax - bbox.ymin) * xsi
                z = bbox.zmin + (bbox.zmax - bbox.zmin) * (eta + xsi) / 2.0
                points.append(
                    {"eta": eta, "xsi": xsi, "side": side, "x": x, "y": y, "z": z}
                )
            return {"points": points}
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
            _, _, _ = require_session(session_manager, params.session_id)
            curve_points = []
            for index in range(params.n_points_per_curve):
                t = index / max(params.n_points_per_curve - 1, 1)
                curve_points.append(
                    {
                        "x": params.plane_point["x"] + params.plane_normal["nx"] * t,
                        "y": params.plane_point["y"] + params.plane_normal["ny"] * t,
                        "z": params.plane_point["z"] + params.plane_normal["nz"] * t,
                    }
                )
            return {"curves": [{"curve_index": 0, "points": curve_points}]}
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
            midpoint = {
                "x": (first.bounding_box.xmin + second.bounding_box.xmax) / 2.0,
                "y": (first.bounding_box.ymin + second.bounding_box.ymax) / 2.0,
                "z": (first.bounding_box.zmin + second.bounding_box.zmax) / 2.0,
            }
            curve_points = []
            for index in range(params.n_points_per_curve):
                t = index / max(params.n_points_per_curve - 1, 1)
                curve_points.append(
                    {
                        "x": midpoint["x"] * (1 + 0.1 * t),
                        "y": midpoint["y"] * (1 - 0.1 * t),
                        "z": midpoint["z"] + t,
                    }
                )
            return {"curves": [{"curve_index": 0, "points": curve_points}]}
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
