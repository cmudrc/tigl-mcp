"""The containerised TiGL path: closed-solid STEP first, real areas recorded.

Found 2026-09-14: TiGL's own ``exportFusedSTEP`` writes open shells in
millimetres with only one half of a symmetric wing, which Gmsh cannot
volume-mesh. The March D150 STEP that every SU2 run used came from the
pythonocc closed-solid procedure instead. These tests pin the adapter's order
of preference and the labelling, and that per-component areas are written to
CPACS only when real TiGL supplied them. ``_run_tigl_script_in_docker`` is the
only thing replaced; it is the container boundary.
"""

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

import pytest

from tigl_mcp import cpacs_adapter

STEP = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"

_CLOSED_REPORT = {
    "tigl_version": "3.5.0-rc1",
    "included": ["wing W1", "wing W1 mirrored", "fuselage F1"],
    "failed": [],
    "nacelles_pylons_included": False,
    "solids_before_fuse": 3,
    "fuse_failures": 0,
    "fused_surface_area_m2": 719.2387,
    "fused_extent_m": [37.684, 33.927, 9.996],
    "step_write_status": 1,
}
_GEOMETRY = {
    "tigl_version": "3.5.0-rc1",
    "wings": [
        {
            "uid": "W1",
            "surface_area_m2": 131.70,
            "wetted_area_m2": 114.07,
            "span_m": 33.93,
            "symmetry": 2,
        }
    ],
    "fuselages": [{"uid": "F1", "surface_area_m2": 415.94, "volume_m3": 381.79}],
    "errors": [],
}


def _no_native_tigl(*_a, **_k):
    raise RuntimeError("no native tigl")


def _fake_runner(responses: dict[str, dict[str, bytes] | None]):
    """Route by the output names each caller asks for."""
    calls: list[tuple[str, ...]] = []

    def run(cpacs_xml, script, out_names, docker_image="tigl-mcp:dev", **_k):
        calls.append(tuple(out_names))
        return responses.get(out_names[0])

    return run, calls


def test_export_step_prefers_closed_solids_and_labels_it(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, calls = _fake_runner(
        {
            "output.step": {
                "output.step": STEP,
                "output.json": json.dumps(_CLOSED_REPORT).encode(),
            }
        }
    )
    monkeypatch.setattr(cpacs_adapter, "_run_tigl_script_in_docker", run)
    monkeypatch.setattr(cpacs_adapter, "build_handles", _no_native_tigl)
    step, source = cpacs_adapter.export_step(sample_cpacs_xml)
    assert step == STEP
    assert source == "docker_tigl_closed_solids"
    assert calls == [("output.step", "output.json")]


def test_export_step_falls_back_to_shells_but_says_so(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run(cpacs_xml, script, out_names, docker_image="tigl-mcp:dev", **_k):
        if out_names == ("output.step", "output.json"):
            return {
                "output.json": json.dumps(
                    {"error": "fuse failed", "included": []}
                ).encode()
            }
        if out_names == ("output.step",):
            return {"output.step": STEP}
        return None

    monkeypatch.setattr(cpacs_adapter, "_run_tigl_script_in_docker", run)
    monkeypatch.setattr(cpacs_adapter, "build_handles", _no_native_tigl)
    step, source = cpacs_adapter.export_step(sample_cpacs_xml)
    assert step == STEP
    assert source == "docker_tigl_fused_shells_mm"


def test_export_step_unavailable_without_docker(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cpacs_adapter, "_run_tigl_script_in_docker", lambda *a, **k: None
    )
    monkeypatch.setattr(cpacs_adapter, "build_handles", _no_native_tigl)
    assert cpacs_adapter.export_step(sample_cpacs_xml) == (None, "unavailable")


def test_cad_tool_route_prefers_closed_solids(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, calls = _fake_runner(
        {"output.step": {"output.step": STEP, "output.json": b"{}"}}
    )
    monkeypatch.setattr(cpacs_adapter, "_run_tigl_script_in_docker", run)
    assert cpacs_adapter._try_export_cad_via_docker(sample_cpacs_xml, "step") == STEP
    assert calls[0] == ("output.step", "output.json")


def test_run_adapter_records_areas_and_fused_body(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    def run(cpacs_xml, script, out_names, docker_image="tigl-mcp:dev", **_k):
        if out_names == ("output.step", "output.json"):
            return {
                "output.step": STEP,
                "output.json": json.dumps(_CLOSED_REPORT).encode(),
            }
        if out_names == ("geometry.json",):
            return {"geometry.json": json.dumps(_GEOMETRY).encode()}
        return None

    monkeypatch.setattr(cpacs_adapter, "_run_tigl_script_in_docker", run)
    real_build = cpacs_adapter.build_handles

    def build(cpacs_xml, uid):
        # read_from_cpacs needs the parser; export_step's native-TiGL probe must fail
        import inspect

        caller = inspect.stack()[1].function
        if caller == "export_step":
            raise RuntimeError("no native tigl")
        return real_build(cpacs_xml, uid)

    monkeypatch.setattr(cpacs_adapter, "build_handles", build)
    xml, results = cpacs_adapter.run_adapter(sample_cpacs_xml, output_dir=str(tmp_path))

    wing = next(c for c in results["components"] if c["uid"] == "W1")
    fuse = next(c for c in results["components"] if c["uid"] == "F1")
    # symmetric wing: TiGL's one-side value doubled, and the note says so
    assert wing["surface_area_m2"] == pytest.approx(2 * 131.70)
    assert wing["wetted_area_m2"] == pytest.approx(2 * 114.07)
    assert wing["span_m"] == pytest.approx(33.93)
    assert "both sides written" in wing["area_note"]
    assert fuse["surface_area_m2"] == pytest.approx(415.94)
    assert results["fused_surface_area_m2"] == pytest.approx(719.2387)
    assert results["tigl_version"] == "3.5.0-rc1"
    assert results["step_source"] == "docker_tigl_closed_solids"
    assert (tmp_path / "aircraft_fused.step").read_bytes() == STEP

    tigl_el = ET.fromstring(xml).find(".//analysisResults/tigl")
    assert tigl_el is not None
    assert tigl_el.findtext("tiglVersion") == "3.5.0-rc1"
    assert tigl_el.findtext("fusedBody/surfaceAreaM2") == "719.239"
    assert tigl_el.findtext("fusedBody/nacellesPylonsIncluded") == "false"
    comps = {c.findtext("uid"): c for c in tigl_el.findall("components/component")}
    assert comps["W1"].findtext("wettedAreaM2") == f"{2 * 114.07:.4f}"
    assert comps["F1"].findtext("surfaceAreaM2") == "415.9400"
    assert comps["W1"].find("boundingBox") is None


def test_run_adapter_without_docker_writes_no_areas(
    sample_cpacs_xml: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cpacs_adapter, "_run_tigl_script_in_docker", lambda *a, **k: None
    )
    real_build = cpacs_adapter.build_handles

    def build(cpacs_xml, uid):
        import inspect

        if inspect.stack()[1].function == "export_step":
            raise RuntimeError("no native tigl")
        return real_build(cpacs_xml, uid)

    monkeypatch.setattr(cpacs_adapter, "build_handles", build)
    xml, results = cpacs_adapter.run_adapter(sample_cpacs_xml)
    assert results["step_source"] == "unavailable"
    assert "fused_surface_area_m2" not in results
    tigl_el = ET.fromstring(xml).find(".//analysisResults/tigl")
    assert tigl_el.find("fusedBody") is None
    assert all(
        c.find("wettedAreaM2") is None for c in tigl_el.findall("components/component")
    )
