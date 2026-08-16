"""Coverage for deterministic configuration CAD export behavior."""

from __future__ import annotations

import base64

import pytest

from tigl_mcp import cpacs_adapter
from tigl_mcp.errors import MCPError
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition
from tigl_mcp.tools import build_tools


def _tool_by_name(tools: list[ToolDefinition], name: str) -> ToolDefinition:
    """Return the named tool definition."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool '{name}' not found")


def test_export_configuration_cad_includes_cpacs_contents(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CAD export returns strict shape plus CPACS payload."""
    manager = SessionManager()
    tools = build_tools(manager)

    open_tool = _tool_by_name(tools, "open_cpacs")
    export_tool = _tool_by_name(tools, "export_configuration_cad")

    open_result = open_tool.handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )
    session_id = open_result["session_id"]

    real_step = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_cad_via_docker", lambda *a, **k: real_step
    )

    result = export_tool.handler({"session_id": session_id, "format": "step"})

    decoded_cpacs = base64.b64decode(result["cpacs_xml_base64"]).decode()

    # Without native bindings the tool now routes to the same containerised
    # TiGL the pipeline adapter uses, rather than returning the CPACS text
    # relabelled as CAD (the old "stub" source, f"cad:step:{cpacs_xml}").
    assert result["source"] == "docker_tigl"
    assert base64.b64decode(result["cad_base64"]) == real_step
    assert decoded_cpacs == sample_cpacs_xml


def test_export_configuration_cad_fails_without_a_kernel(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no kernel reachable, CAD export raises instead of faking a file."""
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_cad_via_docker", lambda *a, **k: None
    )
    manager = SessionManager()
    tools = build_tools(manager)

    session_id = _tool_by_name(tools, "open_cpacs").handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )["session_id"]

    with pytest.raises(MCPError) as excinfo:
        _tool_by_name(tools, "export_configuration_cad").handler(
            {"session_id": session_id, "format": "step"}
        )

    error = excinfo.value.to_dict()["error"]
    assert error["type"] == "CadExportUnavailable"
    assert "TiGL" in str(error["details"])
