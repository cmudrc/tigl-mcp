"""Shared-CPACS adapter for the TiGL MCP.

Reads geometry data from the CPACS XML using the real TiGL MCP parsing
tools, optionally exports STEP geometry (via Docker TiGL when native
libraries aren't available), and writes analysis results back into
``//vehicles/aircraft/model/analysisResults/tigl``.
"""

from __future__ import annotations

import json
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


def _docker_ready(docker_image: str) -> bool:
    """Return True when the Docker daemon answers and the TiGL image is present."""
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        if proc.returncode != 0:
            LOGGER.debug("Docker not available")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    proc2 = subprocess.run(
        ["docker", "images", "-q", docker_image],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if not proc2.stdout.strip():
        LOGGER.debug("Docker image %s not found", docker_image)
        return False
    return True


def _run_tigl_script_in_docker(
    cpacs_xml: str,
    script: str,
    out_names: tuple[str, ...],
    docker_image: str = "tigl-mcp:dev",
    timeout: int = 120,
    label: str = "TiGL script",
) -> dict[str, bytes] | None:
    """Run a Python script against the real TiGL runtime inside the container.

    The CPACS document is mounted as ``/work/input.xml``; the script is mounted
    as ``/work/script.py`` and may write any of ``out_names`` under ``/work``.
    Returns the bytes of every output file that exists, or None if Docker is
    unavailable, the container fails, or none of the outputs appeared. Nothing
    is synthesised on failure; callers decide whether to fall back or raise.
    """
    if not _docker_ready(docker_image):
        return None

    with tempfile.TemporaryDirectory(prefix="tigl_export_") as tmpdir:
        work = Path(tmpdir)
        (work / "input.xml").write_text(cpacs_xml, encoding="utf-8")
        (work / "script.py").write_text(script, encoding="utf-8")
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
                    "/work/script.py",
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            LOGGER.warning("Docker %s timed out after %ss", label, timeout)
            return None
        except Exception as exc:
            LOGGER.warning("Docker %s error: %s", label, exc)
            return None

        outputs = {
            name: (work / name).read_bytes()
            for name in out_names
            if (work / name).exists() and (work / name).stat().st_size > 0
        }
        if not outputs:
            LOGGER.warning(
                "Docker %s produced no output (exit %s): %s",
                label,
                result.returncode,
                result.stderr[-500:],
            )
            return None
        return outputs


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

    Note: TiGL's own STEP exporters write the lofts as shells, in millimetres,
    without the mirrored half of a symmetric wing. That file is fine for CAD
    viewing but cannot be volume-meshed. Use the closed-solid export for CFD.
    """
    # Drive the real TiGL library directly rather than importing this package
    # from inside the image. The container only has to provide a working
    # tigl3/tixi3 runtime, so it stays valid as this package evolves.
    script = (
        "from tixi3 import tixi3wrapper\n"
        "from tigl3 import tigl3wrapper\n"
        "tixi = tixi3wrapper.Tixi3()\n"
        "tixi.open('/work/input.xml')\n"
        "tigl = tigl3wrapper.Tigl3()\n"
        "tigl.open(tixi, '')\n"
        f"tigl.{tigl_call}\n"
    )
    outputs = _run_tigl_script_in_docker(
        cpacs_xml, script, (out_name,), docker_image, timeout=120, label=label
    )
    if not outputs:
        return None
    out_bytes = outputs[out_name]
    if out_bytes.lstrip().startswith(magic):
        LOGGER.info("%s export via Docker succeeded (%d bytes)", label, len(out_bytes))
        return out_bytes
    LOGGER.warning("Docker produced unexpected %s output", label)
    return None


#: Runs inside the container. Same procedure as
#: ``tigl_mcp.tools.export._make_closed_solid_step``: every wing and fuselage
#: loft (and the mirrored loft of a symmetric component) is closed into a solid
#: with OpenCASCADE, the solids are fused into one body, and the body is written
#: as STEP in metres. That is the only export Gmsh can volume-mesh; TiGL's own
#: exportFusedSTEP writes open shells in millimetres with one wing half. The
#: report records what went in, so a reader knows nacelles and pylons are not
#: part of the meshed geometry.
_CLOSED_SOLID_STEP_SCRIPT = r"""
import json, time
report = {"included": [], "failed": [], "nacelles_pylons_included": False}
t0 = time.time()
try:
    from tixi3 import tixi3wrapper
    from tigl3 import tigl3wrapper
    from tigl3 import configuration as tconf
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeSolid
    from OCC.Core.ShapeFix import ShapeFix_Shell
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCC.Core.Interface import Interface_Static_SetCVal
    from OCC.Core.TopAbs import TopAbs_SHELL
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopoDS import topods
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_SurfaceProperties
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib_Add

    tixi = tixi3wrapper.Tixi3(); tixi.open("/work/input.xml")
    tigl = tigl3wrapper.Tigl3(); tigl.open(tixi, "")
    report["tigl_version"] = tigl.getVersion()
    cfg = tconf.CCPACSConfigurationManager_get_instance().get_configuration(tigl._handle.value)

    def shells_to_solids(shape, label):
        out = []
        ex = TopExp_Explorer(shape, TopAbs_SHELL)
        while ex.More():
            shell = topods.Shell(ex.Current())
            if not shell.Closed():
                fx = ShapeFix_Shell(shell); fx.Perform(); shell = fx.Shell()
            mk = BRepBuilderAPI_MakeSolid(shell)
            if mk.IsDone():
                out.append(mk.Solid())
            else:
                report["failed"].append(label + ": shell to solid failed")
            ex.Next()
        if not out:
            report["failed"].append(label + ": no shell")
        return out

    solids = []
    for kind, count, getter in (("wing", cfg.get_wing_count(), cfg.get_wing),
                                ("fuselage", cfg.get_fuselage_count(), cfg.get_fuselage)):
        for i in range(1, count + 1):
            comp = getter(i); uid = comp.get_uid()
            s = shells_to_solids(comp.get_loft().shape(), kind + " " + uid)
            solids += s
            if s:
                report["included"].append(kind + " " + uid)
            try:
                m = comp.get_mirrored_loft()
            except Exception:
                m = None
            if m is not None:
                s2 = shells_to_solids(m.shape(), kind + " " + uid + " mirrored")
                solids += s2
                if s2:
                    report["included"].append(kind + " " + uid + " mirrored")
    report["solids_before_fuse"] = len(solids)
    if solids:
        fused = solids[0]; fails = 0
        for s in solids[1:]:
            fz = BRepAlgoAPI_Fuse(fused, s)
            if fz.IsDone():
                fused = fz.Shape()
            else:
                fails += 1
        report["fuse_failures"] = fails
        p = GProp_GProps(); brepgprop_SurfaceProperties(fused, p)
        report["fused_surface_area_m2"] = p.Mass()
        bb = Bnd_Box(); brepbndlib_Add(fused, bb); x0, y0, z0, x1, y1, z1 = bb.Get()
        report["fused_extent_m"] = [x1 - x0, y1 - y0, z1 - z0]
        Interface_Static_SetCVal("write.step.unit", "M")
        wr = STEPControl_Writer(); wr.Transfer(fused, STEPControl_AsIs)
        report["step_write_status"] = int(wr.Write("/work/output.step"))
except Exception as exc:
    report["error"] = type(exc).__name__ + ": " + str(exc)
report["seconds"] = round(time.time() - t0, 1)
json.dump(report, open("/work/output.json", "w"), indent=1)
"""


#: Runs inside the container. Asks real TiGL for the per-component surface and
#: wetted areas, spans and fuselage volumes. TiGL reports one side of a
#: symmetric wing; the caller doubles it and says so.
_GEOMETRY_QUERY_SCRIPT = r"""
import json
out = {"wings": [], "fuselages": [], "errors": []}
def attempt(name, fn):
    try:
        return fn()
    except Exception as exc:
        out["errors"].append(name + ": " + type(exc).__name__ + ": " + str(exc)); return None
try:
    from tixi3 import tixi3wrapper
    from tigl3 import tigl3wrapper
    tixi = tixi3wrapper.Tixi3(); tixi.open("/work/input.xml")
    tigl = tigl3wrapper.Tigl3(); tigl.open(tixi, "")
    out["tigl_version"] = attempt("getVersion", tigl.getVersion)
    for i in range(1, (attempt("getWingCount", tigl.getWingCount) or 0) + 1):
        uid = attempt("wingGetUID", lambda: tigl.wingGetUID(i))
        out["wings"].append({
            "uid": uid,
            "surface_area_m2": attempt("wingGetSurfaceArea", lambda: tigl.wingGetSurfaceArea(i)),
            "wetted_area_m2": attempt("wingGetWettedArea", lambda: tigl.wingGetWettedArea(uid)),
            "span_m": attempt("wingGetSpan", lambda: tigl.wingGetSpan(uid)),
            "symmetry": attempt("wingGetSymmetry", lambda: int(tigl.wingGetSymmetry(i))),
        })
    for i in range(1, (attempt("getFuselageCount", tigl.getFuselageCount) or 0) + 1):
        uid = attempt("fuselageGetUID", lambda: tigl.fuselageGetUID(i))
        out["fuselages"].append({
            "uid": uid,
            "surface_area_m2": attempt("fuselageGetSurfaceArea", lambda: tigl.fuselageGetSurfaceArea(i)),
            "volume_m3": attempt("fuselageGetVolume", lambda: tigl.fuselageGetVolume(i)),
        })
except Exception as exc:
    out["errors"].append(type(exc).__name__ + ": " + str(exc))
json.dump(out, open("/work/geometry.json", "w"), indent=1)
"""


def _try_export_closed_solid_step_via_docker(
    cpacs_xml: str, docker_image: str = "tigl-mcp:dev", timeout: int = 900
) -> tuple[bytes, dict[str, Any]] | None:
    """Closed-solid, metre-unit, both-halves STEP from real TiGL in Docker.

    Returns (step_bytes, report) or None. The report lists the components that
    went into the fused body and the surface area of that body, which is the
    whole-aircraft wetted area of the geometry as exported.
    """
    outputs = _run_tigl_script_in_docker(
        cpacs_xml,
        _CLOSED_SOLID_STEP_SCRIPT,
        ("output.step", "output.json"),
        docker_image,
        timeout=timeout,
        label="closed-solid STEP",
    )
    if not outputs or "output.step" not in outputs:
        if outputs and "output.json" in outputs:
            LOGGER.warning(
                "closed-solid STEP: %s",
                outputs["output.json"].decode("utf-8", "replace")[:500],
            )
        return None
    step_bytes = outputs["output.step"]
    if not step_bytes.lstrip().startswith(b"ISO-10303-21"):
        return None
    report: dict[str, Any] = {}
    if "output.json" in outputs:
        try:
            report = json.loads(outputs["output.json"].decode("utf-8"))
        except ValueError:
            report = {}
    return step_bytes, report


def _query_geometry_via_docker(
    cpacs_xml: str, docker_image: str = "tigl-mcp:dev", timeout: int = 300
) -> dict[str, Any] | None:
    """Per-component surface/wetted areas from real TiGL in Docker, or None."""
    outputs = _run_tigl_script_in_docker(
        cpacs_xml,
        _GEOMETRY_QUERY_SCRIPT,
        ("geometry.json",),
        docker_image,
        timeout=timeout,
        label="geometry query",
    )
    if not outputs:
        return None
    try:
        return json.loads(outputs["geometry.json"].decode("utf-8"))
    except (KeyError, ValueError):
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
    if cad_format == "step":
        closed = _try_export_closed_solid_step_via_docker(cpacs_xml, docker_image)
        if closed is not None:
            return closed[0]
        LOGGER.warning(
            "closed-solid STEP export failed; falling back to TiGL exportFusedSTEP "
            "(shells, millimetres, one wing half: not volume-meshable)"
        )
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


#: Report of the most recent closed-solid export, kept so ``run_adapter`` can
#: record the fused body without changing ``export_step``'s return type.
_LAST_CLOSED_SOLID_REPORT: dict[str, Any] = {}


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

    closed = _try_export_closed_solid_step_via_docker(cpacs_xml, docker_image)
    if closed is not None:
        _LAST_CLOSED_SOLID_REPORT.clear()
        _LAST_CLOSED_SOLID_REPORT.update(closed[1])
        return closed[0], "docker_tigl_closed_solids"

    docker_step = _run_tigl_export_in_docker(
        cpacs_xml,
        "exportFusedSTEP('/work/output.step')",
        "output.step",
        b"ISO-10303-21",
        "STEP",
        docker_image,
    )
    if docker_step:
        # Shells in millimetres without the mirrored wing half. Kept so a CAD
        # viewer still gets geometry, but labelled so no one meshes it.
        return docker_step, "docker_tigl_fused_shells_mm"

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
    if results.get("tigl_version"):
        ET.SubElement(tigl_el, "tiglVersion").text = str(results["tigl_version"])
    if results.get("geometry_source"):
        ET.SubElement(tigl_el, "geometrySource").text = str(results["geometry_source"])
    # Surface area of the fused closed body that was exported for meshing: the
    # whole-aircraft wetted area of exactly the geometry the CFD will see.
    if results.get("fused_surface_area_m2") is not None:
        fused_el = ET.SubElement(tigl_el, "fusedBody")
        ET.SubElement(
            fused_el, "surfaceAreaM2"
        ).text = f"{results['fused_surface_area_m2']:.3f}"
        if results.get("fused_extent_m"):
            ET.SubElement(fused_el, "extentM").text = " ".join(
                f"{v:.3f}" for v in results["fused_extent_m"]
            )
        if results.get("fused_components") is not None:
            ET.SubElement(fused_el, "components").text = "; ".join(
                results["fused_components"]
            )
        ET.SubElement(fused_el, "nacellesPylonsIncluded").text = str(
            bool(results.get("nacelles_pylons_included", False))
        ).lower()

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
        # Areas are written only when real TiGL computed them. For a symmetric
        # wing TiGL reports one side; both sides are written and the note says so.
        for key, tag in (
            ("surface_area_m2", "surfaceAreaM2"),
            ("wetted_area_m2", "wettedAreaM2"),
            ("span_m", "spanM"),
            ("volume_m3", "volumeM3"),
        ):
            if comp.get(key) is not None:
                ET.SubElement(comp_el, tag).text = f"{comp[key]:.4f}"
        if comp.get("area_note"):
            ET.SubElement(comp_el, "areaNote").text = str(comp["area_note"])
        # A boundingBox element is written only when a real geometry kernel
        # produced one. It is omitted rather than estimated.
        if comp.get("bounding_box"):
            bb = comp["bounding_box"]
            bb_el = ET.SubElement(comp_el, "boundingBox")
            for axis in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
                ET.SubElement(bb_el, axis).text = f"{bb.get(axis, 0.0):.6f}"

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _merge_docker_geometry(
    cpacs_xml: str, results: dict[str, Any], docker_image: str = "tigl-mcp:dev"
) -> None:
    """Attach real TiGL geometry (areas, spans) to ``results`` in place.

    When Docker is not available nothing is added; the components keep only
    what the CPACS file states.
    """
    geom = _query_geometry_via_docker(cpacs_xml, docker_image)
    if not geom:
        return
    by_uid = {c["uid"]: c for c in results.get("components", [])}
    for w in geom.get("wings", []):
        comp = by_uid.get(w.get("uid"))
        if comp is None:
            continue
        both_sides = w.get("symmetry") not in (None, 0)
        factor = 2.0 if both_sides else 1.0
        for key in ("surface_area_m2", "wetted_area_m2"):
            if w.get(key) is not None:
                comp[key] = float(w[key]) * factor
        if w.get("span_m") is not None:
            comp["span_m"] = float(w["span_m"])
        comp["area_note"] = (
            "TiGL wingGetSurfaceArea / wingGetWettedArea; symmetric wing, one side "
            "reported by TiGL, both sides written"
            if both_sides
            else "TiGL wingGetSurfaceArea / wingGetWettedArea"
        )
    for f in geom.get("fuselages", []):
        comp = by_uid.get(f.get("uid"))
        if comp is None:
            continue
        if f.get("surface_area_m2") is not None:
            comp["surface_area_m2"] = float(f["surface_area_m2"])
        if f.get("volume_m3") is not None:
            comp["volume_m3"] = float(f["volume_m3"])
        comp["area_note"] = (
            "TiGL fuselageGetSurfaceArea (skin under wing and tail roots included)"
        )
    if geom.get("tigl_version"):
        results["tigl_version"] = geom["tigl_version"]
    results["geometry_source"] = (
        f"tigl {geom.get('tigl_version', '?')} in {docker_image}"
    )
    if geom.get("errors"):
        results["geometry_query_errors"] = geom["errors"]


def run_adapter(
    cpacs_xml: str,
    output_dir: str | None = None,
    existing_step_path: str | None = None,
    docker_image: str = "tigl-mcp:dev",
) -> tuple[str, dict[str, Any]]:
    """Full read→process→write cycle for the TiGL domain.

    Also attempts STEP export and saves it for downstream SU2 use, and, when
    the containerised TiGL is reachable, records per-component surface and
    wetted areas and the surface area of the fused body that was exported.
    """
    results = read_from_cpacs(cpacs_xml)

    step_bytes, step_source = export_step(
        cpacs_xml,
        existing_step_path=existing_step_path,
        docker_image=docker_image,
    )

    results["step_source"] = step_source
    results["step_bytes"] = step_bytes
    if step_source == "docker_tigl_closed_solids" and _LAST_CLOSED_SOLID_REPORT:
        rep = dict(_LAST_CLOSED_SOLID_REPORT)
        results["fused_surface_area_m2"] = rep.get("fused_surface_area_m2")
        results["fused_extent_m"] = rep.get("fused_extent_m")
        results["fused_components"] = rep.get("included")
        results["nacelles_pylons_included"] = rep.get("nacelles_pylons_included", False)
        if rep.get("failed"):
            results["fused_component_failures"] = rep["failed"]
        if rep.get("tigl_version"):
            results["tigl_version"] = rep["tigl_version"]

    _merge_docker_geometry(cpacs_xml, results, docker_image)

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
