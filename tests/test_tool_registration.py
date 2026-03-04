"""Contract tests for tool registration and error surfaces."""

from __future__ import annotations

import pytest

from tigl_mcp_server.errors import MCPError
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools import build_tools


def test_build_tools_registers_expected_stub_toolset() -> None:
    """The server exposes the current deterministic tool catalog."""
    tools = build_tools(SessionManager())

    assert [tool.name for tool in tools] == [
        "open_cpacs",
        "close_cpacs",
        "get_configuration_summary",
        "list_geometric_components",
        "get_component_metadata",
        "get_wing_summary",
        "get_fuselage_summary",
        "sample_component_surface",
        "intersect_with_plane",
        "intersect_components",
        "export_component_mesh",
        "export_configuration_cad",
        "get_high_level_parameters",
        "set_high_level_parameters",
    ]


def test_tool_validate_rejects_extra_parameters() -> None:
    """Pydantic-backed parameter models keep the public tool surface strict."""
    open_tool = build_tools(SessionManager())[0]

    with pytest.raises(ValueError):
        open_tool.validate(
            {
                "source_type": "xml_string",
                "source": "<cpacs />",
                "unexpected": True,
            }
        )


def test_invalid_session_uses_structured_mcp_errors() -> None:
    """Session lookup failures preserve structured error payloads."""
    summary_tool = next(
        tool
        for tool in build_tools(SessionManager())
        if tool.name == "get_configuration_summary"
    )

    with pytest.raises(MCPError) as error_info:
        summary_tool.handler({"session_id": "missing"})

    assert error_info.value.error["error"]["type"] == "InvalidSession"
    assert error_info.value.error["error"]["message"] == "Unknown session_id 'missing'"
