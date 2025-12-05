"""Coverage for component mesh export behaviors."""

from __future__ import annotations

import base64
from collections.abc import Iterable

import pytest

from tigl_mcp_server.errors import MCPError
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition
from tigl_mcp_server.tools import build_tools


def _tool_by_name(tools: Iterable[ToolDefinition], name: str) -> ToolDefinition:
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool '{name}' not found")


def _open_session(manager: SessionManager, cpacs_xml: str) -> str:
    tools = build_tools(manager)
    open_tool = _tool_by_name(tools, "open_cpacs")
    result = open_tool.handler({"source_type": "xml_string", "source": cpacs_xml})
    session_id = result["session_id"]
    if not isinstance(session_id, str):
        raise AssertionError("Session id must be a string")
    return session_id


def test_export_component_mesh_prefers_tigl_su2(sample_cpacs_xml: str) -> None:
    """Direct TiGL SU2 export wins when the capability is available."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)
    _, tigl_handle, _ = manager.get(session_id)

    def fake_export(uid: str) -> bytes:
        return b"NDIME= 3\nNPOIN= 0\n"

    tigl_handle.exportSU2 = fake_export  # type: ignore[attr-defined]

    mesh_tool = _tool_by_name(tools, "export_component_mesh")
    result = mesh_tool.handler(
        {
            "session_id": session_id,
            "component_uid": "W1",
            "format": "su2",
        }
    )

    decoded = base64.b64decode(result["mesh_base64"])
    assert decoded.startswith(b"NDIME= 3")


def test_export_component_mesh_rejects_unsupported_su2(
    sample_cpacs_xml: str,
) -> None:
    """SU2 exports fail clearly when TiGL lacks support."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    mesh_tool = _tool_by_name(tools, "export_component_mesh")

    with pytest.raises(MCPError) as excinfo:
        mesh_tool.handler(
            {
                "session_id": session_id,
                "component_uid": "W1",
                "format": "su2",
            }
        )

    assert "format 'su2' not supported" in str(excinfo.value)
    assert "W1" in str(excinfo.value)


def test_export_component_mesh_returns_ascii_stl(sample_cpacs_xml: str) -> None:
    """STL exports return format-like payloads, not handles."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    mesh_tool = _tool_by_name(tools, "export_component_mesh")
    result = mesh_tool.handler(
        {
            "session_id": session_id,
            "component_uid": "W1",
            "format": "stl",
        }
    )

    mesh_bytes = base64.b64decode(result["mesh_base64"])
    assert mesh_bytes.startswith(b"solid W1")
    assert b"vertex" in mesh_bytes
