"""End-to-end coverage for the tigl_mcp_server tools."""

from __future__ import annotations

import pytest

from tigl_mcp.tools import ToolDefinition
from tigl_mcp_server.errors import MCPError
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools import build_tools
from tigl_mcp_server.tools.parameters import set_high_level_parameters_tool


def _tool_by_name(tools: list[ToolDefinition], name: str) -> ToolDefinition:
    """Locate a tool by name in the provided collection."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool '{name}' not found")


def test_open_and_summarize_configuration(sample_cpacs_xml: str) -> None:
    """Opening a CPACS string registers a session and exposes summaries."""
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
    assert summary["bounding_box"]["xmax"] > summary["bounding_box"]["xmin"]

    close_result = close_tool.handler({"session_id": session_id})
    assert close_result["success"] is True

    with pytest.raises(MCPError):
        summary_tool.handler({"session_id": session_id})


def test_parameter_updates_support_relative_changes(sample_cpacs_xml: str) -> None:
    """set_high_level_parameters applies relative and absolute updates."""
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


def test_invalid_session_produces_structured_error() -> None:
    """Missing sessions raise MCPError with structured payload."""
    manager = SessionManager()
    tools = build_tools(manager)
    summary_tool = _tool_by_name(tools, "get_configuration_summary")

    with pytest.raises(MCPError) as error_info:
        summary_tool.handler({"session_id": "missing"})

    assert error_info.value.error["error"]["type"] == "InvalidSession"
