"""Parameter inspection and update tools."""

from __future__ import annotations

from tigl_mcp.tools import ToolDefinition, ToolParameters
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools.common import require_session


class GetParametersParams(ToolParameters):
    """Parameters for get_high_level_parameters."""

    session_id: str
    component_uid: str


class SetParametersParams(ToolParameters):
    """Parameters for set_high_level_parameters."""

    session_id: str
    component_uid: str
    updates: dict[str, float | str]


def _apply_update(current: float | None, update_value: float | str) -> float:
    """Apply an update string or numeric value to a parameter."""
    if isinstance(update_value, (int, float)):
        return float(update_value)
    if isinstance(update_value, str):
        if update_value.endswith("%"):
            if current is None:
                raise_mcp_error(
                    "UpdateError", "Cannot apply percentage to unknown value"
                )
            delta = float(update_value.rstrip("%")) / 100.0
            return current * (1.0 + delta)
        if update_value.startswith(("+", "-")):
            if current is None:
                raise_mcp_error(
                    "UpdateError", "Cannot apply relative change to unknown value"
                )
            return current + float(update_value)
        return float(update_value)
    raise_mcp_error("UpdateError", "Unsupported update type")


def get_high_level_parameters_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the get_high_level_parameters tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = GetParametersParams(**raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )
            return {"component_uid": component.uid, "parameters": component.parameters}
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("ParameterError", "Failed to fetch parameters", str(exc))

    return ToolDefinition(
        name="get_high_level_parameters",
        description="Return high-level design parameters for a component.",
        parameters_model=GetParametersParams,
        handler=handler,
        output_schema={},
    )


def set_high_level_parameters_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the set_high_level_parameters tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = SetParametersParams(**raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )
            warnings: list[str] = []
            for key, value in params.updates.items():
                current_value = component.parameters.get(key)
                try:
                    component.parameters[key] = _apply_update(current_value, value)
                except MCPError:
                    raise
                except Exception as exc:  # pragma: no cover - defensive path
                    warnings.append(f"Skipped '{key}': {exc}")
            return {
                "component_uid": component.uid,
                "new_parameters": component.parameters,
                "warnings": warnings,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "ParameterError", "Failed to apply parameter updates", str(exc)
            )

    return ToolDefinition(
        name="set_high_level_parameters",
        description="Update high-level design parameters and return the new values.",
        parameters_model=SetParametersParams,
        handler=handler,
        output_schema={},
    )
