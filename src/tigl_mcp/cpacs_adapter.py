"""Shared-CPACS adapter for the TiGL MCP.

Reads geometry data from the CPACS XML using the real TiGL MCP parsing
tools, optionally exports STEP geometry (via Docker TiGL when native
libraries aren't available), and writes analysis results back into
``//vehicles/aircraft/model/analysisResults/tigl``.
"""

from __future__ import annotations

import base64
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from tigl_mcp.cpacs import build_handles, parse_cpacs

LOGGER = logging.getLogger(__name__)


def read_from_cpacs(cpacs_xml: str) -> dict[str, Any]:
    """Extract inputs the TiGL MCP needs from CPACS XML.

    Uses the real TiGL MCP parsing functions.
    """
    _, _, configuration, metadata = build_handles(cpacs_xml, None)

    components = []
    for comp in configuration.all_components():
        components.append({
            "uid": comp.uid,
            "name": comp.name,
            "type": comp.type_name,
            "index": comp.index,
            "symmetry": comp.symmetry,
            "bounding_box": {
                "xmin": comp.bounding_box.xmin,
                "xmax": comp.bounding_box.xmax,
                "ymin": comp.bounding_box.ymin,
                "ymax": comp.bounding_box.ymax,
                "zmin": comp.bounding_box.zmin,
                "zmax": comp.bounding_box.zmax,
            },
        })

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
        "ref_area_m2": float(ref_area_el.text) if ref_area_el is not None and ref_area_el.text else None,
        "ref_length_m": float(ref_length_el.text) if ref_length_el is not None and ref_length_el.text else None,
    }


def _try_export_step_via_docker(
    cpacs_xml: str,
    docker_image: str = "tigl-mcp:dev",
) -> bytes | None:
    """Attempt STEP export by calling the TiGL MCP inside Docker.

    Returns the STEP file bytes on success, None on failure.
    """
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5,
        )
        if proc.returncode != 0:
            LOGGER.debug("Docker not available")
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    proc = subprocess.run(
        ["docker", "images", "-q", docker_image],
        capture_output=True, text=True, timeout=5,
    )
    if not proc.stdout.strip():
        LOGGER.debug("Docker image %s not found", docker_image)
        return None

    with tempfile.TemporaryDirectory(prefix="tigl_step_") as tmpdir:
        cpacs_path = Path(tmpdir) / "input.xml"
        cpacs_path.write_text(cpacs_xml, encoding="utf-8")

        script = (
            "import json, base64, sys; "
            "sys.path.insert(0, '/app/src'); "
            "from tigl_mcp.session_manager import SessionManager; "
            "from tigl_mcp.tools.export import export_configuration_cad_tool; "
            "from tigl_mcp.tools.cpacs_io import open_cpacs_tool; "
            "sm = SessionManager(); "
            "open_fn = open_cpacs_tool(sm); "
            "r = open_fn.handler({'source_type': 'path', 'source': '/work/input.xml'}); "
            "sid = r['session_id']; "
            "export_fn = export_configuration_cad_tool(sm); "
            "r2 = export_fn.handler({'session_id': sid, 'format': 'step'}); "
            "print(json.dumps({'source': r2.get('source'), 'cad_base64': r2.get('cad_base64', '')[:100]+'...'})); "
            "with open('/work/output.step', 'wb') as f: f.write(base64.b64decode(r2['cad_base64'])); "
        )

        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-v", f"{tmpdir}:/work",
                    docker_image,
                    "python", "-c", script,
                ],
                capture_output=True, text=True, timeout=120,
            )
            step_path = Path(tmpdir) / "output.step"
            if result.returncode == 0 and step_path.exists():
                step_bytes = step_path.read_bytes()
                if step_bytes.lstrip().startswith(b"ISO-10303-21"):
                    LOGGER.info("STEP export via Docker succeeded (%d bytes)", len(step_bytes))
                    return step_bytes
                LOGGER.warning("Docker produced non-STEP output")
            else:
                LOGGER.warning("Docker STEP export failed: %s", result.stderr[:500])
        except subprocess.TimeoutExpired:
            LOGGER.warning("Docker STEP export timed out")
        except Exception as exc:
            LOGGER.warning("Docker STEP export error: %s", exc)

    return None


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

        if hasattr(tigl_handle, 'exportFusedSTEP') or hasattr(tigl_handle, 'exportSTEP'):
            from tigl_mcp.tools.export import _export_configuration_cad_bytes_via_tigl
            step_bytes = _export_configuration_cad_bytes_via_tigl(tigl_handle, "step")
            if step_bytes and step_bytes.lstrip().startswith(b"ISO-10303-21"):
                return step_bytes, "tigl_native"
    except Exception as exc:
        LOGGER.debug("Native TiGL STEP export not available: %s", exc)

    step_bytes = _try_export_step_via_docker(cpacs_xml, docker_image)
    if step_bytes:
        return step_bytes, "docker_tigl"

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
