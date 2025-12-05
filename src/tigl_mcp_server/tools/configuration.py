"""Tools for inspecting CPACS configurations."""

from __future__ import annotations

from tigl_mcp_server.cpacs import ComponentDefinition
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters
from tigl_mcp_server.tools.common import format_bounding_box, require_session


class SessionOnlyParams(ToolParameters):
    """Parameters that only require a session identifier."""

    session_id: str


class ListComponentsParams(SessionOnlyParams):
    """Parameters for list_geometric_components."""

    type_filter: str | None = None


class ComponentMetadataParams(SessionOnlyParams):
    """Parameters for get_component_metadata."""

    component_uid: str


def _component_to_dict(component: ComponentDefinition) -> dict[str, object]:
    """Convert a component into a JSON-serializable dictionary."""
    return {
        "uid": component.uid,
        "name": component.name,
        "index": component.index,
        "type": component.type_name,
        "parent_uid": None,
        "label": component.name,
        "symmetry": component.symmetry,
        "bounding_box": format_bounding_box(component.bounding_box),
        "parameters": component.parameters,
    }


def get_configuration_summary_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the get_configuration_summary tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = SessionOnlyParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            bounding_box = format_bounding_box(config.bounding_box())
            wings = [
                {"uid": wing.uid, "name": wing.name, "index": wing.index}
                for wing in config.wings
            ]
            fuselages = [
                {"uid": fuselage.uid, "name": fuselage.name, "index": fuselage.index}
                for fuselage in config.fuselages
            ]
            rotors = [
                {"uid": rotor.uid, "name": rotor.name, "index": rotor.index}
                for rotor in config.rotors
            ]
            engines = [
                {"uid": engine.uid, "name": engine.name, "index": engine.index}
                for engine in config.engines
            ]
            return {
                "wings": wings,
                "fuselages": fuselages,
                "rotors": rotors,
                "engines": engines,
                "bounding_box": bounding_box,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "SummaryError", "Failed to build configuration summary", str(exc)
            )

    return ToolDefinition(
        name="get_configuration_summary",
        description="Return component lists and the overall bounding box.",
        parameters_model=SessionOnlyParams,
        handler=handler,
        output_schema={},
    )


def list_geometric_components_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the list_geometric_components tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, list[dict[str, object]]]:
        try:
            params = ListComponentsParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            components: list[dict[str, object]] = [
                _component_to_dict(component) for component in config.all_components()
            ]
            if params.type_filter:
                components = [
                    component
                    for component in components
                    if str(component["type"]).lower() == params.type_filter.lower()
                ]
            for component in components:
                component.pop("parameters", None)
                component.pop("symmetry", None)
                component.pop("bounding_box", None)
            return {"components": components}
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("ListError", "Failed to list components", str(exc))

    return ToolDefinition(
        name="list_geometric_components",
        description="List CPACS geometric components.",
        parameters_model=ListComponentsParams,
        handler=handler,
        output_schema={},
    )


def get_component_metadata_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the get_component_metadata tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = ComponentMetadataParams.model_validate(raw_params)
            _, _, config = require_session(session_manager, params.session_id)
            component = config.find_component(params.component_uid)
            if component is None:
                raise_mcp_error(
                    "NotFound", f"Component '{params.component_uid}' not found"
                )
            metadata: dict[str, object] = {
                "uid": component.uid,
                "type": component.type_name,
                "parent_uid": None,
                "children_uids": [],
                "symmetry": component.symmetry,
                "bounding_box": format_bounding_box(component.bounding_box),
                "wing_data": None,
                "fuselage_data": None,
            }
            if component.type_name.lower() == "wing":
                metadata["wing_data"] = {
                    "num_sections": component.parameters.get("sections", 0),
                    "num_segments": component.parameters.get("segments", 0),
                    "num_component_segments": component.parameters.get(
                        "component_segments", 0
                    ),
                }
            if component.type_name.lower() == "fuselage":
                metadata["fuselage_data"] = {
                    "num_segments": component.parameters.get("segments", 0)
                }
            metadata["bounding_box"] = format_bounding_box(component.bounding_box)
            return metadata
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "MetadataError", "Failed to read component metadata", str(exc)
            )

    return ToolDefinition(
        name="get_component_metadata",
        description="Return metadata for a geometric component.",
        parameters_model=ComponentMetadataParams,
        handler=handler,
        output_schema={},
    )
