"""Coverage for deterministic component mesh export behavior."""

from __future__ import annotations

import base64
from collections.abc import Iterable

import pytest

from tigl_mcp import cpacs_adapter
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
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SU2 exports convert real TiGL STL output through meshio."""
    real_stl = (
        b"solid W1\n"
        b"  facet normal 0 0 1\n"
        b"    outer loop\n"
        b"      vertex 12.744 0.0 0.0\n"
        b"      vertex 22.137 0.0 0.0\n"
        b"      vertex 17.0 16.963 0.0\n"
        b"    endloop\n"
        b"  endfacet\n"
        b"endsolid W1\n"
    )
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_mesh_via_docker", lambda *a, **k: real_stl
    )
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


def test_export_component_mesh_su2_fails_without_a_kernel(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The SU2 path must not fall back to a synthetic STL either."""
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_mesh_via_docker", lambda *a, **k: None
    )
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    with pytest.raises(MCPError) as excinfo:
        _tool_by_name(tools, "export_component_mesh").handler(
            {"session_id": session_id, "component_uid": "W1", "format": "su2"}
        )

    assert excinfo.value.to_dict()["error"]["type"] == "MeshExportUnavailable"


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


def test_export_component_mesh_fails_without_a_kernel(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Meshing without TiGL raises instead of returning a synthetic triangle.

    The old behaviour returned the same single triangle -- vertices (0,0,0),
    (0,1,0), (1,0,0) -- for every component of every aircraft. The kernel is
    stubbed out here so the test is deterministic on hosts with and without
    Docker.
    """
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_mesh_via_docker", lambda *a, **k: None
    )
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    mesh_tool = _tool_by_name(tools, "export_component_mesh")
    with pytest.raises(MCPError) as excinfo:
        mesh_tool.handler(
            {"session_id": session_id, "component_uid": "W1", "format": "stl"}
        )

    error = excinfo.value.to_dict()["error"]
    assert error["type"] == "MeshExportUnavailable"
    assert "TiGL" in str(error["details"])


def test_export_component_mesh_returns_real_tigl_output(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a kernel is reachable, its bytes are returned unmodified."""
    real_stl = (
        b"solid W1\n"
        b"  facet normal 0 0 1\n"
        b"    outer loop\n"
        b"      vertex 12.744 0.0 0.0\n"
        b"      vertex 22.137 0.0 0.0\n"
        b"      vertex 17.0 16.963 0.0\n"
        b"    endloop\n"
        b"  endfacet\n"
        b"endsolid W1\n"
    )
    captured: dict[str, object] = {}

    def fake_mesh(cpacs_xml, uid, component_type, mesh_format="stl", **kwargs):
        captured.update(uid=uid, component_type=component_type, fmt=mesh_format)
        return real_stl

    monkeypatch.setattr(cpacs_adapter, "_try_export_mesh_via_docker", fake_mesh)
    manager = SessionManager()
    session_id = _open_session(manager, sample_cpacs_xml)
    tools = build_tools(manager)

    result = _tool_by_name(tools, "export_component_mesh").handler(
        {"session_id": session_id, "component_uid": "W1", "format": "stl"}
    )

    assert base64.b64decode(result["mesh_base64"]) == real_stl
    assert result["num_triangles"] == 1
    # The UID and type are what select TiGL's per-component exporter.
    assert captured == {"uid": "W1", "component_type": "Wing", "fmt": "stl"}
