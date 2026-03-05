"""Coverage for deterministic component mesh export behavior."""

from __future__ import annotations

import base64
from collections.abc import Iterable

import pytest

from tigl_mcp.errors import MCPError
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition
from tigl_mcp.tools import build_tools
from tigl_mcp.tools.export import _count_stl_triangles, _looks_like_stl_payload


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


def test_count_stl_triangles_handles_binary_stl_payload() -> None:
    """Binary STL payloads return the header triangle count."""
    binary_stl = b"\x00" * 80 + (2).to_bytes(4, byteorder="little") + (b"\x00" * 100)

    assert _count_stl_triangles(binary_stl) == 2


def test_looks_like_stl_payload_accepts_small_valid_ascii_stl() -> None:
    """Small valid ASCII STL payloads are recognized as real STL."""
    small_ascii_stl = (
        b"solid tiny\n"
        b"facet normal 0 0 0\n"
        b"  outer loop\n"
        b"    vertex 0 0 0\n"
        b"    vertex 0 1 0\n"
        b"    vertex 1 0 0\n"
        b"  endloop\n"
        b"endfacet\n"
        b"endsolid tiny\n"
    )

    assert _looks_like_stl_payload(small_ascii_stl) is True


def test_export_component_mesh_converts_su2_via_meshio(
    sample_cpacs_xml: str,
) -> None:
    """SU2 exports use STL conversion and return valid SU2 content."""
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

    decoded = base64.b64decode(result["mesh_base64"])
    assert decoded.startswith(b"NDIME=")


def test_export_component_mesh_rejects_unknown_component(
    sample_cpacs_xml: str,
) -> None:
    """Requesting a non-existent component raises NotFound."""
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    mesh_tool = _tool_by_name(tools, "export_component_mesh")

    with pytest.raises(MCPError) as excinfo:
        mesh_tool.handler(
            {
                "session_id": session_id,
                "component_uid": "DOES_NOT_EXIST",
                "format": "stl",
            }
        )

    assert excinfo.value.error["error"]["type"] == "NotFound"


def test_export_component_mesh_returns_ascii_stl(sample_cpacs_xml: str) -> None:
    """STL export returns deterministic bytes with triangle count from payload."""
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
    assert result["num_triangles"] == 1
