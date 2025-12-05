"""Coverage for component mesh export behaviors."""

from __future__ import annotations

import base64
from collections.abc import Iterable

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
        return f"su2:{uid}".encode()

    tigl_handle.exportSU2 = fake_export  # type: ignore[attr-defined]

    mesh_tool = _tool_by_name(tools, "export_component_mesh")
    result = mesh_tool.handler(
        {
            "session_id": session_id,
            "component_uid": "W1",
            "format": "su2",
        }
    )

    decoded = base64.b64decode(result["mesh_base64"]).decode("utf-8")
    assert decoded == "su2:W1"


def test_export_component_mesh_converts_stl_to_su2(sample_cpacs_xml: str) -> None:
    """STL exports are converted to SU2 when TiGL lacks support."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    mesh_tool = _tool_by_name(tools, "export_component_mesh")
    result = mesh_tool.handler(
        {
            "session_id": session_id,
            "component_uid": "W1",
            "format": "su2",
        }
    )

    decoded = base64.b64decode(result["mesh_base64"]).decode("utf-8")
    assert decoded.startswith("su2-from-stl:W1:")
    assert "mesh:stl:W1" in decoded
