"""Shared-CPACS adapter for the TiGL MCP.

Reads geometry data from the CPACS XML using the real TiGL MCP parsing
tools, optionally exports STEP geometry (via Docker TiGL when native
libraries aren't available), and writes analysis results back into
``//vehicles/aircraft/model/analysisResults/tigl``.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from tigl_mcp.cpacs import build_handles

LOGGER = logging.getLogger(__name__)


def read_from_cpacs(cpacs_xml: str) -> dict[str, Any]:
    """Extract inputs the TiGL MCP needs from CPACS XML.

    Uses the real TiGL MCP parsing functions.
    """
    _, _, configuration, metadata = build_handles(cpacs_xml, None)

    # Only facts stated in the CPACS file are reported here. Bounding boxes are
    # deliberately absent: CPACS does not carry them, and deriving one needs a
    # real TiGL kernel. Writing an estimate into the shared document would put
    # an untraceable number into the digital thread.
    components = []
    for comp in configuration.all_components():
        components.append(
            {
                "uid": comp.uid,
                "name": comp.name,
                "type": comp.type_name,
                "index": comp.index,
                "symmetry": comp.symmetry,
                "section_count": comp.section_count,
                "segment_count": comp.segment_count,
            }
        )

    root = ET.fromstring(cpacs_xml)
    ref_area_el = root.find(".//vehicles/aircraft/model/reference/area")
    ref_length_el = root.find(".//vehicles/aircraft/model/reference/length")

    return {
        "metadata": metadata,
        "wing_count": len(configuration.wings),
        "fuselage_count": len(configuration.fuselages),
        "rotor_count": len(configuration.rotors),
        "engine_count": len(configuration.engines),
        "components": components,
        "ref_area_m2": float(ref_area_el.text)
        if ref_area_el is not None and ref_area_el.text
        else None,
        "ref_length_m": float(ref_length_el.text)
        if ref_length_el is not None and ref_length_el.text
        else None,
    }


#: Per-format details for the containerised export: the TiGL method to call,
#: the output file name, and the magic bytes a valid file starts with.
_DOCKER_CAD_FORMATS: dict[str, tuple[str, str, bytes]] = {
    "step": ("exportFusedSTEP", "output.step", b"ISO-10303-21"),
    "iges": ("exportIGES", "output.igs", b""),
}


def _run_tigl_export_in_docker(
    cpacs_xml: str,
    tigl_call: str,
    out_name: str,
    magic: bytes,
    label: str,
    docker_image: str = "tigl-mcp:dev",
) -> bytes | None:
    """Run one TiGL export call inside the container and return the file bytes.

    ``tigl_call`` is a Python expression invoked on an opened ``tigl`` handle,
    e.g. ``exportFusedSTEP('/work/output.step')``. Returns None on any failure,
    so callers can decide whether to fall back or raise.
    """
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        if proc.returncode != 0:
            LOGGER.debug("Docker not available")
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    proc2 = subprocess.run(
        ["docker", "images", "-q", docker_image],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if not proc2.stdout.strip():
        LOGGER.debug("Docker image %s not found", docker_image)
        return None

    with tempfile.TemporaryDirectory(prefix="tigl_export_") as tmpdir:
        cpacs_path = Path(tmpdir) / "input.xml"
        cpacs_path.write_text(cpacs_xml, encoding="utf-8")

        # Drive the real TiGL library directly rather than importing this
        # package from inside the image. The container only has to provide a
        # working tigl3/tixi3 runtime, so it stays valid as this package
        # evolves.
        script = (
            "from tixi3 import tixi3wrapper; "
            "from tigl3 import tigl3wrapper; "
            "tixi = tixi3wrapper.Tixi3(); "
            "tixi.open('/work/input.xml'); "
            "tigl = tigl3wrapper.Tigl3(); "
            "tigl.open(tixi, ''); "
            f"tigl.{tigl_call}; "
        )

        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    # The image is linux/amd64; be explicit so Apple Silicon
                    # hosts emulate instead of warning about the mismatch.
                    "--platform",
                    "linux/amd64",
                    "-v",
                    f"{tmpdir}:/work",
                    docker_image,
                    "python",
                    "-c",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            out_path = Path(tmpdir) / out_name
            if result.returncode == 0 and out_path.exists():
                out_bytes = out_path.read_bytes()
                if out_bytes.lstrip().startswith(magic):
                    LOGGER.info(
                        "%s export via Docker succeeded (%d bytes)",
                        label,
                        len(out_bytes),
                    )
                    return out_bytes
                LOGGER.warning("Docker produced unexpected %s output", label)
            else:
                LOGGER.warning(
                    "Docker %s export failed: %s", label, result.stderr[:500]
                )
        except subprocess.TimeoutExpired:
            LOGGER.warning("Docker %s export timed out", label)
        except Exception as exc:
            LOGGER.warning("Docker %s export error: %s", label, exc)

    return None


def _try_export_cad_via_docker(
    cpacs_xml: str,
    cad_format: str = "step",
    docker_image: str = "tigl-mcp:dev",
) -> bytes | None:
    """Export whole-configuration CAD by driving real TiGL inside Docker."""
    fmt = _DOCKER_CAD_FORMATS.get(cad_format)
    if fmt is None:
        LOGGER.debug("Unsupported Docker CAD format %s", cad_format)
        return None
    method, out_name, magic = fmt
    return _run_tigl_export_in_docker(
        cpacs_xml,
        f"{method}('/work/{out_name}')",
        out_name,
        magic,
        cad_format.upper(),
        docker_image,
    )


def _try_export_step_via_docker(
    cpacs_xml: str,
    docker_image: str = "tigl-mcp:dev",
) -> bytes | None:
    """Back-compatible STEP-only wrapper around :func:`_try_export_cad_via_docker`."""
    return _try_export_cad_via_docker(cpacs_xml, "step", docker_image)


#: TiGL's per-component mesh exporters, keyed by (component type, format).
#: Meshing is per component and by UID, so a caller gets the geometry of the
#: part it named rather than the whole aircraft.
_DOCKER_MESH_METHODS: dict[tuple[str, str], tuple[str, str, bytes]] = {
    ("wing", "stl"): ("exportMeshedWingSTLByUID", "mesh.stl", b"solid"),
    ("fuselage", "stl"): ("exportMeshedFuselageSTLByUID", "mesh.stl", b"solid"),
    ("wing", "vtk"): ("exportMeshedWingVTKByUID", "mesh.vtk", b"# vtk"),
    ("fuselage", "vtk"): ("exportMeshedFuselageVTKByUID", "mesh.vtk", b"# vtk"),
}


def _try_export_mesh_via_docker(
    cpacs_xml: str,
    component_uid: str,
    component_type: str,
    mesh_format: str = "stl",
    deflection: float = 0.01,
    docker_image: str = "tigl-mcp:dev",
) -> bytes | None:
    """Export a real surface mesh for one component via TiGL inside Docker."""
    key = (component_type.lower(), mesh_format.lower())
    entry = _DOCKER_MESH_METHODS.get(key)
    if entry is None:
        LOGGER.debug("No TiGL mesh exporter for %s/%s", component_type, mesh_format)
        return None
    method, out_name, magic = entry

    # UIDs come from the CPACS file, but quote defensively: this string is
    # interpolated into a Python expression run inside the container.
    if "'" in component_uid or "\\" in component_uid:
        LOGGER.warning("Refusing unsafe component UID %r", component_uid)
        return None

    return _run_tigl_export_in_docker(
        cpacs_xml,
        f"{method}('{component_uid}', '/work/{out_name}', {float(deflection)})",
        out_name,
        magic,
        f"{component_type} {mesh_format.upper()}",
        docker_image,
    )


def export_step(
    cpacs_xml: str,
    existing_step_path: str | None = None,
    docker_image: str = "tigl-mcp:dev",
) -> tuple[bytes | None, str]:
    """Export STEP geometry from CPACS.

    Tries in order:
    1. Use an existing STEP file if provided
    2. Use native TiGL libraries (tigl3/tixi3)
    3. Use Docker TiGL image

    Returns (step_bytes, source_description).
    """
    if existing_step_path:
        p = Path(existing_step_path)
        if p.exists() and p.stat().st_size > 0:
            return p.read_bytes(), f"existing_file:{existing_step_path}"

    try:
        from tigl_mcp.cpacs import build_handles

        _, tigl_handle, _, _ = build_handles(cpacs_xml, None)

        if hasattr(tigl_handle, "exportFusedSTEP") or hasattr(
            tigl_handle, "exportSTEP"
        ):
            from tigl_mcp.tools.export import _export_configuration_cad_bytes_via_tigl

            step_bytes = _export_configuration_cad_bytes_via_tigl(tigl_handle, "step")
            if step_bytes and step_bytes.lstrip().startswith(b"ISO-10303-21"):
                return step_bytes, "tigl_native"
    except Exception as exc:
        LOGGER.debug("Native TiGL STEP export not available: %s", exc)

    docker_step = _try_export_step_via_docker(cpacs_xml, docker_image)
    if docker_step:
        return docker_step, "docker_tigl"

    return None, "unavailable"


def write_to_cpacs(cpacs_xml: str, results: dict[str, Any]) -> str:
    """Write TiGL analysis results back into the CPACS XML."""
    root = ET.fromstring(cpacs_xml)

    model = root.find(".//vehicles/aircraft/model")
    if model is None:
        model = _ensure_path(root, "vehicles/aircraft/model")

    ar = model.find("analysisResults")
    if ar is None:
        ar = ET.SubElement(model, "analysisResults")

    existing = ar.find("tigl")
    if existing is not None:
        ar.remove(existing)

    tigl_el = ET.SubElement(ar, "tigl")
    ET.SubElement(tigl_el, "wingCount").text = str(results.get("wing_count", 0))
    ET.SubElement(tigl_el, "fuselageCount").text = str(results.get("fuselage_count", 0))
    ET.SubElement(tigl_el, "rotorCount").text = str(results.get("rotor_count", 0))
    ET.SubElement(tigl_el, "engineCount").text = str(results.get("engine_count", 0))

    if results.get("step_source"):
        ET.SubElement(tigl_el, "stepExportSource").text = results["step_source"]
    if results.get("step_path"):
        ET.SubElement(tigl_el, "stepFilePath").text = results["step_path"]

    components_el = ET.SubElement(tigl_el, "components")
    for comp in results.get("components", []):
        comp_el = ET.SubElement(components_el, "component")
        ET.SubElement(comp_el, "uid").text = comp["uid"]
        ET.SubElement(comp_el, "name").text = comp.get("name", comp["uid"])
        ET.SubElement(comp_el, "type").text = comp.get("type", "unknown")
        for key, tag in (
            ("section_count", "sectionCount"),
            ("segment_count", "segmentCount"),
        ):
            if comp.get(key) is not None:
                ET.SubElement(comp_el, tag).text = str(comp[key])
        # A boundingBox element is written only when a real geometry kernel
        # produced one. It is omitted rather than estimated.
        if comp.get("bounding_box"):
            bb = comp["bounding_box"]
            bb_el = ET.SubElement(comp_el, "boundingBox")
            for axis in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
                ET.SubElement(bb_el, axis).text = f"{bb.get(axis, 0.0):.6f}"

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def run_adapter(
    cpacs_xml: str,
    output_dir: str | None = None,
    existing_step_path: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """Full read→process→write cycle for the TiGL domain.

    Also attempts STEP export and saves it for downstream SU2 use.
    """
    results = read_from_cpacs(cpacs_xml)

    step_bytes, step_source = export_step(
        cpacs_xml,
        existing_step_path=existing_step_path,
    )

    results["step_source"] = step_source
    results["step_bytes"] = step_bytes

    if step_bytes and output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        step_path = out / "aircraft_fused.step"
        step_path.write_bytes(step_bytes)
        results["step_path"] = str(step_path)

    updated_xml = write_to_cpacs(cpacs_xml, results)
    return updated_xml, results


def _ensure_path(root: ET.Element, path: str) -> ET.Element:
    current = root
    for part in path.split("/"):
        child = current.find(part)
        if child is None:
            child = ET.SubElement(current, part)
        current = child
    return current
