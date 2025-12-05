"""Regression coverage for configuration CAD exports."""

from __future__ import annotations

import base64

from tigl_mcp.tools import ToolDefinition
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools import build_tools


def _tool_by_name(tools: list[ToolDefinition], name: str) -> ToolDefinition:
    for tool in tools:
        if tool.name == name:
            return tool
    msg = f"Tool '{name}' not found"
    raise AssertionError(msg)


def test_export_configuration_cad_includes_cpacs_contents(
    sample_cpacs_xml: str,
) -> None:
    """Exports include the CPACS payload, not just metadata."""
    manager = SessionManager()
    tools = build_tools(manager)

    open_tool = _tool_by_name(tools, "open_cpacs")
    export_tool = _tool_by_name(tools, "export_configuration_cad")

    open_result = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )
    session_id = open_result["session_id"]

    result = export_tool.handler({"session_id": session_id, "format": "step"})

    decoded = base64.b64decode(result["cad_base64"]).decode()
    assert "<cpacs>" in decoded
    assert sample_cpacs_xml.strip() in decoded
