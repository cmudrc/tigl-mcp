"""The geometry check: the lofts real TiGL built against what the file says.

Added 2026-10-07. On renders of the public D150 with its main wing on one
side only, or displaced 6 m above the fuselage, the multimodal observer
reported a normal aircraft (0 of 8 faults found at 4 B and at 27 B
parameters), and the numbers-only arm accepted a lift coefficient of 13.3
from a wrong reference area. Those are properties of the geometry, so they
are checked from the lofts here. The numbers in these fixtures are the ones
real TiGL in Docker returned for those cases on 2026-10-07; only the Docker
boundary is replaced.
"""

from __future__ import annotations

import json
from xml.etree import ElementTree as ET

import pytest

from tigl_mcp import cpacs_adapter
from tigl_mcp.cpacs_adapter import check_geometry, geometry_faults_from_cpacs

FUSELAGE_BOX = {
    "xmin": 0.0,
    "xmax": 37.68,
    "ymin": -1.98,
    "ymax": 1.98,
    "zmin": -2.17,
    "zmax": 1.98,
}
WING_BOX = {
    "xmin": 12.74,
    "xmax": 22.14,
    "ymin": -16.96,
    "ymax": 16.96,
    "zmin": -1.85,
    "zmax": -0.11,
}
VTP_BOX = {
    "xmin": 29.94,
    "xmax": 36.83,
    "ymin": -0.33,
    "ymax": 0.33,
    "zmin": 1.96,
    "zmax": 7.82,
}


def _d150(**overrides):
    wing = {
        "uid": "D150_wing_1ID",
        "type": "Wing",
        "tigl_symmetry": 2,
        "tigl_reference_area_m2": 61.22,
        "bounding_box": dict(WING_BOX),
        "min_distance_to_fuselage_m": {"D150Fuselage1ID": 0.0},
    }
    vtp = {
        "uid": "D150_VTP_1ID",
        "type": "Wing",
        "tigl_symmetry": 0,
        "tigl_reference_area_m2": 0.02,
        "bounding_box": dict(VTP_BOX),
        "min_distance_to_fuselage_m": {"D150Fuselage1ID": 0.032},
    }
    fus = {
        "uid": "D150Fuselage1ID",
        "type": "Fuselage",
        "bounding_box": dict(FUSELAGE_BOX),
    }
    results = {
        "ref_area_m2": 122.4,
        "components": [wing, vtp, fus],
        "fused_components": [
            "wing D150_wing_1ID",
            "wing D150_wing_1ID mirrored",
            "wing D150_VTP_1ID",
            "fuselage D150Fuselage1ID",
        ],
    }
    results.update(overrides)
    return results


def _types(check):
    return sorted(f["type"] for f in check["findings"])


def test_intact_d150_has_no_findings_and_the_vertical_tail_is_not_one_sided():
    check = check_geometry(_d150())
    assert check["checked"] is True
    assert check["findings"] == []
    assert "one_sided:D150_VTP_1ID" in check["checks_run"]
    assert check["tolerances"]["attachment_m"] == pytest.approx(0.3768, rel=1e-3)


def test_wing_on_one_side_only_is_a_fault():
    r = _d150()
    r["components"][0]["tigl_symmetry"] = 0
    r["components"][0]["bounding_box"]["ymin"] = -0.0
    check = check_geometry(r)
    assert _types(check) == ["wing_one_side_only"]
    f = check["findings"][0]
    assert f["severity"] == "fault" and f["component"] == "D150_wing_1ID"
    assert "right (+y)" in f["message"]


def test_detached_wing_is_a_fault_with_the_measured_gap():
    r = _d150()
    r["components"][0]["min_distance_to_fuselage_m"] = {"D150Fuselage1ID": 2.179}
    check = check_geometry(r)
    assert _types(check) == ["wing_detached"]
    assert check["findings"][0]["measured"]["min_distance_m"] == 2.179
    assert "2.179 m" in check["findings"][0]["message"]


def test_small_gap_within_tolerance_is_not_a_fault():
    r = _d150()
    r["components"][0]["min_distance_to_fuselage_m"] = {"D150Fuselage1ID": 0.2}
    assert check_geometry(r)["findings"] == []


def test_wrong_reference_area_is_a_fault_and_a_test_body_is_not():
    r = _d150(ref_area_m2=3.0)
    check = check_geometry(r)
    assert _types(check) == ["reference_area_inconsistent"]
    assert check["findings"][0]["measured"]["ratio"] == pytest.approx(
        3.0 / 122.44, rel=1e-3
    )
    # The canard test body states 1.0 m2 against a 2.3 m2 planform: inside the band.
    canard = {
        "ref_area_m2": 1.0,
        "components": [
            {
                "uid": "Wing",
                "type": "Wing",
                "tigl_symmetry": 2,
                "tigl_reference_area_m2": 1.15,
                "bounding_box": {
                    "xmin": 0,
                    "xmax": 1,
                    "ymin": -1.5,
                    "ymax": 1.5,
                    "zmin": -0.06,
                    "zmax": 0.06,
                },
                "min_distance_to_fuselage_m": {"SimpleFuselage": 0.0},
            },
            {
                "uid": "SimpleFuselage",
                "type": "Fuselage",
                "bounding_box": {
                    "xmin": -0.5,
                    "xmax": 1.5,
                    "ymin": -0.56,
                    "ymax": 0.56,
                    "zmin": -0.56,
                    "zmax": 0.5,
                },
            },
        ],
    }
    assert check_geometry(canard)["findings"] == []


def test_canard_wing_displaced_one_metre_is_detached():
    canard = {
        "ref_area_m2": 1.0,
        "components": [
            {
                "uid": "Wing",
                "type": "Wing",
                "tigl_symmetry": 2,
                "tigl_reference_area_m2": 1.15,
                "bounding_box": {
                    "xmin": 0,
                    "xmax": 1,
                    "ymin": -1.5,
                    "ymax": 1.5,
                    "zmin": 0.94,
                    "zmax": 1.06,
                },
                "min_distance_to_fuselage_m": {"SimpleFuselage": 0.44},
            },
            {
                "uid": "SimpleFuselage",
                "type": "Fuselage",
                "bounding_box": {
                    "xmin": -0.5,
                    "xmax": 1.5,
                    "ymin": -0.56,
                    "ymax": 0.56,
                    "zmin": -0.56,
                    "zmax": 0.5,
                },
            },
        ],
    }
    check = check_geometry(canard)
    assert _types(check) == ["wing_detached"]
    assert check["tolerances"]["attachment_m"] == pytest.approx(0.05)


def test_component_left_out_of_the_export_is_a_fault():
    r = _d150(
        fused_components=[
            "wing D150_wing_1ID",
            "wing D150_wing_1ID mirrored",
            "fuselage D150Fuselage1ID",
        ]
    )
    check = check_geometry(r)
    assert _types(check) == ["component_missing_from_export"]
    assert check["findings"][0]["component"] == "D150_VTP_1ID"


def test_nothing_to_check_without_a_kernel_is_said_not_guessed():
    r = {"ref_area_m2": 122.4, "components": [{"uid": "W", "type": "Wing"}]}
    check = check_geometry(r)
    assert check["checked"] is False and check["findings"] == []
    assert "no geometry kernel" in check["reason"]


def test_merge_writes_boxes_and_the_check_into_cpacs(sample_cpacs_xml, monkeypatch):
    geometry = {
        "tigl_version": "3.5.0-rc1",
        "wings": [
            {
                "uid": "W1",
                "surface_area_m2": 10.0,
                "wetted_area_m2": 9.0,
                "span_m": 4.0,
                "symmetry": 0,
                "reference_area_xy_m2": 2.0,
                "bounding_box": {
                    "xmin": 0,
                    "xmax": 1,
                    "ymin": 0.0,
                    "ymax": 2.0,
                    "zmin": 0,
                    "zmax": 0.1,
                },
                "min_distance_to_fuselage_m": {"F1": 0.0},
            }
        ],
        "fuselages": [
            {
                "uid": "F1",
                "surface_area_m2": 20.0,
                "volume_m3": 5.0,
                "bounding_box": {
                    "xmin": -1,
                    "xmax": 3,
                    "ymin": -0.5,
                    "ymax": 0.5,
                    "zmin": -0.5,
                    "zmax": 0.5,
                },
            }
        ],
        "errors": [],
    }

    def run(cpacs_xml, script, out_names, docker_image="tigl-mcp:dev", **_k):
        return {"geometry.json": json.dumps(geometry).encode()}

    monkeypatch.setattr(cpacs_adapter, "_run_tigl_script_in_docker", run)
    results = cpacs_adapter.read_from_cpacs(sample_cpacs_xml)
    uids = {c["uid"] for c in results["components"]}
    # Point the fixture's components at the fake geometry's uids.
    for c in results["components"]:
        if c["type"].lower() == "wing":
            c["uid"] = "W1"
        elif c["type"].lower() == "fuselage":
            c["uid"] = "F1"
    cpacs_adapter._merge_docker_geometry(sample_cpacs_xml, results)
    check = results["geometry_check"]
    assert check["checked"] is True
    assert [f["type"] for f in check["findings"]] == ["wing_one_side_only"]
    wing = next(c for c in results["components"] if c["uid"] == "W1")
    assert wing["bounding_box"]["ymax"] == 2.0 and wing["tigl_symmetry"] == 0

    xml = cpacs_adapter.write_to_cpacs(sample_cpacs_xml, results)
    root = ET.fromstring(xml)
    gc = root.find(".//analysisResults/tigl/geometryChecks")
    assert gc is not None and gc.get("checked") == "true"
    assert gc.findtext("finding/type") == "wing_one_side_only"
    faults = geometry_faults_from_cpacs(xml)
    assert len(faults) == 1 and faults[0]["component"] == "W1"
    assert uids  # the fixture had components to begin with
