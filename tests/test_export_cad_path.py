"""The CAD export hands over a file path, not a 400 KB string.

Found 2026-10-08 in the first Kiro Mode A run: the model copied 528 of
535,928 base64 characters from the export into the mesher. Servers on one
machine hand off by path.
"""

from __future__ import annotations

import base64
from pathlib import Path

from tigl_mcp import cpacs_adapter
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tools import build_tools

REAL_STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nEND-ISO-10303-21;\n"


def _tools(sample_cpacs_xml, monkeypatch):
    monkeypatch.setattr(
        cpacs_adapter, "_try_export_cad_via_docker", lambda *a, **k: REAL_STEP
    )
    manager = SessionManager()
    tools = {t.name: t for t in build_tools(manager)}
    sid = tools["open_cpacs"].handler(
        {"source_type": "xml_string", "source": sample_cpacs_xml}
    )["session_id"]
    return tools, sid


def test_export_returns_a_path_by_default_and_no_blob(
    sample_cpacs_xml, monkeypatch, tmp_path
):
    tools, sid = _tools(sample_cpacs_xml, monkeypatch)
    out = tools["export_configuration_cad"].handler(
        {
            "session_id": sid,
            "format": "step",
            "output_path": str(tmp_path / "a" / "aircraft.step"),
        }
    )
    assert Path(out["cad_path"]).read_bytes() == REAL_STEP
    assert out["cad_bytes"] == len(REAL_STEP)
    assert "cad_base64" not in out
    assert out["source"] == "docker_tigl"


def test_export_without_output_path_uses_a_fresh_temp_file(
    sample_cpacs_xml, monkeypatch
):
    tools, sid = _tools(sample_cpacs_xml, monkeypatch)
    out = tools["export_configuration_cad"].handler(
        {"session_id": sid, "format": "step"}
    )
    assert Path(out["cad_path"]).read_bytes() == REAL_STEP
    assert out["cad_path"].endswith(".step")


def test_base64_is_still_available_on_request(sample_cpacs_xml, monkeypatch):
    tools, sid = _tools(sample_cpacs_xml, monkeypatch)
    out = tools["export_configuration_cad"].handler(
        {"session_id": sid, "format": "step", "include_base64": True}
    )
    assert base64.b64decode(out["cad_base64"]) == REAL_STEP


def test_description_tells_the_client_what_to_pass_on(sample_cpacs_xml, monkeypatch):
    tools, _ = _tools(sample_cpacs_xml, monkeypatch)
    d = tools["export_configuration_cad"].description
    assert "cad_path" in d and "step_path" in d
