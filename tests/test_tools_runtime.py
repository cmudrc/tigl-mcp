"""End-to-end tool coverage for the tool runtime."""

from __future__ import annotations

from pathlib import Path

import pytest

from tigl_mcp.errors import MCPError
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition
from tigl_mcp.tools import build_tools
from tigl_mcp.tools.parameters import set_high_level_parameters_tool


def _tool_by_name(tools: list[ToolDefinition], name: str) -> ToolDefinition:
    """Locate a tool by name in the provided collection."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool '{name}' not found")


def test_open_and_summarize_configuration(sample_cpacs_xml: str) -> None:
    """Opening CPACS XML registers a session and exposes a summary."""
    manager = SessionManager()
    tools = build_tools(manager)
    open_tool = _tool_by_name(tools, "open_cpacs")
    summary_tool = _tool_by_name(tools, "get_configuration_summary")
    close_tool = _tool_by_name(tools, "close_cpacs")

    open_result = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )
    session_id = open_result["session_id"]

    summary = summary_tool.handler({"session_id": session_id})

    assert summary["wings"][0]["uid"] == "W1"
    assert summary["fuselages"][0]["uid"] == "F1"
    # No geometry kernel is wired in, so the envelope is reported as absent
    # with a reason, never as invented numbers.
    assert summary["bounding_box"] is None
    assert "real TiGL kernel" in summary["bounding_box_note"]

    close_result = close_tool.handler({"session_id": session_id})
    assert close_result["success"] is True

    with pytest.raises(MCPError):
        summary_tool.handler({"session_id": session_id})


def test_open_cpacs_supports_path_inputs(sample_cpacs_path: Path) -> None:
    """Path-based opens return the file name in extracted metadata."""
    manager = SessionManager()
    open_tool = _tool_by_name(build_tools(manager), "open_cpacs")

    result = open_tool.handler(
        {"source_type": "path", "source": str(sample_cpacs_path)}
    )

    assert result["cpacs_metadata"]["file_name"] == str(sample_cpacs_path)
    assert result["configuration_summary"]["num_wings"] == 1


def test_parameter_updates_support_relative_changes(sample_cpacs_xml: str) -> None:
    """Parameter mutation uses the values parsed from the file as the baseline."""
    manager = SessionManager()
    open_tool = _tool_by_name(build_tools(manager), "open_cpacs")
    open_result = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )
    session_id = open_result["session_id"]

    setter = set_high_level_parameters_tool(manager)
    update_result = setter.handler(
        {
            "session_id": session_id,
            "component_uid": "W1",
            "updates": {"span": "+10%", "area": 85.0},
        }
    )
    assert update_result["new_parameters"]["span"] == pytest.approx(33.0)
    assert update_result["new_parameters"]["area"] == 85.0


def test_geometry_tools_fail_loudly_without_a_kernel(
    sample_cpacs_xml: str,
) -> None:
    """Geometry operations raise a structured error instead of inventing data.

    These five tools previously returned numbers derived from a bounding box
    that was itself a function of the component's array index. Under the
    project's no-stubs rule a missing kernel must surface as an error that
    names its dependency, so no caller can mistake an estimate for TiGL output.
    """
    manager = SessionManager()
    tools = build_tools(manager)
    open_tool = _tool_by_name(tools, "open_cpacs")

    session_id = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )["session_id"]

    calls = {
        "sample_component_surface": {
            "session_id": session_id,
            "component_uid": "W1",
            "parameterization": "wing_component_segment_eta_xsi",
            "samples": [{"eta": 0.5, "xsi": 0.25, "side": "left"}],
        },
        "intersect_with_plane": {
            "session_id": session_id,
            "component_uid": "W1",
            "plane_point": {"x": 0.0, "y": 0.0, "z": 0.0},
            "plane_normal": {"nx": 1.0, "ny": 0.0, "nz": 0.0},
            "n_points_per_curve": 3,
        },
        "intersect_components": {
            "session_id": session_id,
            "component_uid_one": "W1",
            "component_uid_two": "F1",
            "n_points_per_curve": 4,
        },
        "get_wing_summary": {"session_id": session_id, "wing_uid": "W1"},
        "get_fuselage_summary": {"session_id": session_id, "fuselage_uid": "F1"},
    }

    for tool_name, payload in calls.items():
        with pytest.raises(MCPError) as excinfo:
            _tool_by_name(tools, tool_name).handler(payload)

        error = excinfo.value.to_dict()["error"]
        assert error["type"] == "GeometryUnavailable", tool_name
        # The error must point at the missing dependency, not just complain.
        assert "TiGL" in str(error["details"]), tool_name


def test_unknown_uid_still_reports_not_found(sample_cpacs_xml: str) -> None:
    """A bad UID is a NotFound, not swallowed by the geometry guard."""
    manager = SessionManager()
    tools = build_tools(manager)
    open_tool = _tool_by_name(tools, "open_cpacs")

    session_id = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )["session_id"]

    with pytest.raises(MCPError) as excinfo:
        _tool_by_name(tools, "get_wing_summary").handler(
            {"session_id": session_id, "wing_uid": "NoSuchWing"}
        )

    assert excinfo.value.to_dict()["error"]["type"] == "NotFound"


def test_component_lookup_is_case_insensitive(sample_cpacs_xml: str) -> None:
    """Tool handlers resolve component IDs case-insensitively."""
    manager = SessionManager()
    tools = build_tools(manager)
    open_tool = _tool_by_name(tools, "open_cpacs")
    metadata_tool = _tool_by_name(tools, "get_component_metadata")

    open_result = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )
    session_id = open_result["session_id"]

    metadata = metadata_tool.handler({"session_id": session_id, "component_uid": "w1"})
    assert metadata["uid"] == "W1"


def test_invalid_session_produces_structured_error() -> None:
    """Missing sessions raise MCPError with structured payload."""
    manager = SessionManager()
    tools = build_tools(manager)
    summary_tool = _tool_by_name(tools, "get_configuration_summary")

    with pytest.raises(MCPError) as error_info:
        summary_tool.handler({"session_id": "missing"})

    assert error_info.value.error["error"]["type"] == "InvalidSession"
