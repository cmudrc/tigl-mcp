"""Coverage for deterministic component mesh export behavior."""

from __future__ import annotations

import base64
from collections.abc import Iterable

import pytest

from tigl_mcp.errors import MCPError
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition
from tigl_mcp.tools import build_tools


def _tool_by_name(tools: Iterable[ToolDefinition], name: str) -> ToolDefinition:
    """Locate a tool definition by name."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool '{name}' not found")


def _open_session(manager: SessionManager, cpacs_xml: str) -> str:
    """Create a stub-backed CPACS session and return its id."""
    tools = build_tools(manager)
    open_tool = _tool_by_name(tools, "open_cpacs")
    result = open_tool.handler({"source_type": "xml_string", "source": cpacs_xml})
    session_id = result["session_id"]
    if not isinstance(session_id, str):
        raise AssertionError("Session id must be a string")
    return session_id


def _minimal_stl(uid: str) -> bytes:
    """Create a valid minimal ASCII STL payload for SU2 conversion tests."""
    return (
        f"solid {uid}\n"
        "facet normal 0 0 0\n"
        "  outer loop\n"
        "    vertex 0 0 0\n"
        "    vertex 1 0 0\n"
        "    vertex 0 1 0\n"
        "  endloop\n"
        "endfacet\n"
        f"endsolid {uid}\n"
    ).encode("ascii")


def test_export_component_mesh_converts_su2_via_meshio(
    sample_cpacs_xml: str,
) -> None:
    """SU2 export relies on meshio plus stubbed STL bytes from the runtime."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)
    _, tigl_handle, _ = manager.get(session_id)

    tigl_handle.exportComponentSTL = _minimal_stl  # type: ignore[attr-defined]

    mesh_tool = _tool_by_name(tools, "export_component_mesh")

    result = mesh_tool.handler(
        {
            "session_id": session_id,
            "component_uid": "W1",
            "format": "su2",
        }
    )

    decoded = base64.b64decode(result["mesh_base64"])
    assert decoded.startswith(b"NDIME=")


def test_export_component_mesh_rejects_unsupported_su2(
    sample_cpacs_xml: str,
) -> None:
    """SU2 exports fail clearly when no STL export hook is attached."""
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

    assert excinfo.value.error["error"]["type"] == "MeshExportError"
    assert "Failed to export STL mesh for 'W1' via TiGL" in str(excinfo.value)


def test_export_component_mesh_raises_on_bad_stl(sample_cpacs_xml: str) -> None:
    """Invalid STL inputs trigger MeshExportError during SU2 conversion."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)
    _, tigl_handle, _ = manager.get(session_id)

    tigl_handle.exportComponentSTL = (  # type: ignore[attr-defined]
        lambda uid: b"not-an-stl"
    )

    mesh_tool = _tool_by_name(tools, "export_component_mesh")

    with pytest.raises(MCPError) as excinfo:
        mesh_tool.handler(
            {
                "session_id": session_id,
                "component_uid": "W1",
                "format": "su2",
            }
        )

    assert excinfo.value.error["error"]["type"] == "MeshExportError"


def test_export_component_mesh_returns_ascii_stl(sample_cpacs_xml: str) -> None:
    """STL export returns deterministic ASCII payloads, not opaque handles."""
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
