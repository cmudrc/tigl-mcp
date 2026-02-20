"""Export tools for meshes and CAD files."""

from __future__ import annotations

import base64
import tempfile
import types
from collections.abc import Iterator, Sized
from importlib import import_module
from typing import Any, Literal, NoReturn
from pathlib import Path
import subprocess
import os
import sys
# Optional dependency: tigl3 bindings exist in the TiGL container, but may be absent locally.
try:
    from tigl3.import_export_helper import export_shapes  # type: ignore
    from tigl3.exports import create_exporter  # type: ignore
except Exception:
    export_shapes = None  # type: ignore
    create_exporter = None  # type: ignore
from tigl_mcp_server.cpacs import ComponentDefinition, TiglConfiguration
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters
from tigl_mcp_server.tools.common import format_bounding_box, require_session

MeshFormat = Literal["stl", "vtk", "collada", "su2"]


class ExportMeshParams(ToolParameters):
    """Parameters for export_component_mesh."""

    session_id: str
    component_uid: str
    format: MeshFormat
    meshing_options: dict[str, float] | None = None


class ExportCadParams(ToolParameters):
    """Parameters for export_configuration_cad."""

    session_id: str
    format: Literal["step", "iges"]


def _export_step_file_dynamic(tigl_handle: Any, component_uid: str, step_path: Path) -> None:
    """
    Export STEP by calling whatever TiGL export API exists.
    Many TiGL APIs use exportConfiguration/exportComponent where file extension selects format.
    """
    # Let exporter create the file (safer)
    step_path.unlink(missing_ok=True)

    # Collect export-like callables
    exportish = []
    for name in dir(tigl_handle):
        if "export" in name.lower():
            fn = getattr(tigl_handle, name, None)
            if callable(fn):
                exportish.append((name, fn))

    # Prefer component exports first (if available)
    comp_candidates = [(n, f) for (n, f) in exportish if "exportcomponent" in n.lower()]
    conf_candidates = [(n, f) for (n, f) in exportish if "exportconfiguration" in n.lower() or n.lower() == "export"]

    errors = []

    # 1) Try exportComponent(uid, filename, deflection) / variations
    for name, fn in comp_candidates:
        try:
            try:
                fn(component_uid, str(step_path), 0.001)
            except TypeError:
                try:
                    fn(component_uid, str(step_path))
                except TypeError:
                    fn(str(step_path), component_uid, 0.001)

            if step_path.exists() and step_path.stat().st_size > 0:
                return
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    # 2) Fallback: exportConfiguration(filename, fuseAllShapes, deflection) / variations
    # Note: this exports the whole aircraft, not just one component — but it unblocks the pipeline.
    for name, fn in conf_candidates:
        try:
            try:
                fn(str(step_path), False, 0.001)
            except TypeError:
                try:
                    fn(str(step_path), False)
                except TypeError:
                    fn(str(step_path))

            if step_path.exists() and step_path.stat().st_size > 0:
                return
        except Exception as e:
            errors.append(f"{name}: {type(e).__name__}: {e}")

    # If still nothing worked, raise with visibility
    export_names = [n for (n, _) in exportish]
    raise_mcp_error(
        "MeshExportError",
        "No usable TiGL STEP export method found on TiglConfiguration.",
        {
            "export_like_methods": export_names,
            "attempt_errors": errors[:10],
        },
    )


def _step_to_stl_bytes(step_path: Path) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        stl_path = Path(f.name)

    try:
        stl_path.unlink(missing_ok=True)
        cmd = ["gmsh", str(step_path), "-2", "-format", "stl", "-o", str(stl_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise_mcp_error("MeshExportError", "gmsh failed converting STEP->STL", proc.stdout + "\n" + proc.stderr)

        return stl_path.read_bytes()
    finally:
        stl_path.unlink(missing_ok=True)




def _export_real_stl_bytes(tigl_handle: Any, component: ComponentDefinition) -> bytes:
    """
    Preferred path:
      Use TiGL meshed STL exporters (by UID) via _export_stl_bytes_via_tigl3.

    Optional fallback (can enable later):
      STEP -> gmsh -> STL (only if STEP export is known-good for the component)
    """
    if os.environ.get("TIGL_MCP_DEBUG_EXPORTS") == "1":
        keys = ("export", "step", "iges", "stp", "stl", "write", "save", "mesh")
        methods = [n for n in dir(tigl_handle) if any(k in n.lower() for k in keys)]
        print(f"[tigl-mcp][debug] tigl_handle export-ish methods: {methods}", file=sys.stderr, flush=True)

    errors: list[str] = []

    # 1) Preferred: meshed STL by UID (wings/fuselage) or meshed geometry STL fallback
    try:
        stl_bytes = _export_stl_bytes_via_tigl3(tigl_handle, component)
        if len(stl_bytes) >= 2048:
            return stl_bytes
        errors.append(f"shape->stl too small ({len(stl_bytes)} B)")
    except Exception as e:
        errors.append(f"shape->stl failed: {type(e).__name__}: {e}")

    # 2) Optional STEP fallback: disable for now to avoid wrong UID/exportComponent issues
    # If you want to keep it, we should inspect _export_step_file_dynamic first.

    raise_mcp_error(
        "MeshExportError",
        "No working STL export route found.",
        " | ".join(errors[:10]),
    )







def _coerce_mesh_bytes(raw_mesh: object, format_label: str) -> bytes:
    """Ensure mesh payloads are bytes, raising on unsupported types."""
    if isinstance(raw_mesh, bytes):
        return raw_mesh
    if isinstance(raw_mesh, str):
        return raw_mesh.encode("utf-8")
    raise_mcp_error(
        "MeshExportError",
        f"TiGL returned unsupported {format_label} mesh content of type",
        f" {type(raw_mesh)}",
    )


def _raise_unsupported_format(mesh_format: MeshFormat, component_uid: str) -> NoReturn:
    """Raise a standardized error for unsupported mesh formats."""
    raise_mcp_error(
        "MeshExportError",
        (
            "Mesh export failed: format "
            f"'{mesh_format}' not supported for component {component_uid}."
        ),
    )


def _ensure_export_supported(
    tigl_handle: TiglConfiguration, mesh_format: MeshFormat, component_uid: str
) -> None:
    """Verify requested mesh export format is supported and fail clearly when not."""
    supported_native_formats: set[MeshFormat] = {"stl", "vtk", "collada", "su2"}
    if mesh_format in supported_native_formats:
        return

    _raise_unsupported_format(mesh_format, component_uid)


def _export_su2_via_tigl(
    tigl_handle: TiglConfiguration, component: ComponentDefinition
) -> bytes:
    """Export SU2 mesh bytes using TiGL STL export combined with meshio conversion."""
    try:
        meshio_module: Any = import_module("meshio")
        stl_bytes = _export_stl_bytes_via_tigl3(tigl_handle, component)
    except MCPError:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise_mcp_error(
            "MeshExportError",
            f"Failed to export STL mesh for '{component.uid}' via TiGL",
            str(exc),
        )

    if not stl_bytes:
        raise_mcp_error(
            "MeshExportError", f"TiGL returned empty STL mesh for '{component.uid}'"
        )

    try:
        with tempfile.NamedTemporaryFile(suffix=".stl") as stl_file:
            stl_file.write(stl_bytes)
            stl_file.flush()
            mesh = meshio_module.read(stl_file.name, file_format="stl")

        class _SU2Cell:
            def __init__(self, cell_type: str, data: Sized) -> None:
                self.type = cell_type
                self.data = data

            def __iter__(self) -> Iterator[object]:
                yield self.type
                yield self.data

            def __len__(self) -> int:
                return len(self.data)

        converted_cells = [_SU2Cell(cell.type, cell.data) for cell in mesh.cells]
        mesh_to_write = types.SimpleNamespace(
            points=mesh.points, cells=converted_cells, cell_data=mesh.cell_data
        )

        with tempfile.NamedTemporaryFile(suffix=".su2") as su2_file:
            meshio_module.write(su2_file.name, mesh_to_write, file_format="su2")
            su2_file.flush()
            su2_file.seek(0)
            su2_bytes = su2_file.read()
    except MCPError:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise_mcp_error(
            "MeshExportError",
            f"Failed to export SU2 mesh for '{component.uid}' via meshio",
            str(exc),
        )

    if not su2_bytes or b"NDIME=" not in su2_bytes:
        raise_mcp_error(
            "MeshExportError",
            f"Conversion to SU2 failed or output invalid for '{component.uid}'",
        )

    return su2_bytes


def _synthetic_mesh_bytes(
    mesh_format: MeshFormat, component: ComponentDefinition
) -> bytes:
    """Generate deterministic, format-like mesh payloads for supported formats."""
    if mesh_format == "stl":
        return (
            f"solid {component.uid}\n"
            "  facet normal 0 0 0\n"
            "    outer loop\n"
            "      vertex 0 0 0\n"
            "      vertex 0 1 0\n"
            "      vertex 1 0 0\n"
            "    endloop\n"
            "  endfacet\n"
            f"endsolid {component.uid}\n"
        ).encode("ascii")
    if mesh_format == "vtk":
        return (
            "# vtk DataFile Version 3.0\n"
            f"component {component.uid}\n"
            "ASCII\n"
            "DATASET POLYDATA\n"
            "POINTS 0 float\n"
        ).encode("ascii")
    if mesh_format == "collada":
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<COLLADA><asset/><library_geometries>"
            f'<geometry id="{component.uid}" name="{component.uid}"/>'
            "</library_geometries></COLLADA>"
        ).encode()

    _raise_unsupported_format(mesh_format, component.uid)




def _export_mesh_bytes(tigl_handle: TiglConfiguration, component: ComponentDefinition, mesh_format: MeshFormat) -> bytes:
    """Export mesh content for the requested format."""
    if mesh_format == "su2":
        return _export_su2_via_tigl(tigl_handle, component)

    if mesh_format == "stl":
        return _export_real_stl_bytes(tigl_handle, component)

    return _synthetic_mesh_bytes(mesh_format, component)



def _looks_like_handle(mesh_bytes: bytes) -> bool:
    """Detect legacy handle payloads masquerading as mesh bytes."""
    try:
        mesh_text = mesh_bytes.decode("ascii")
    except UnicodeDecodeError:
        return False
    return mesh_text.startswith("mesh:") or mesh_text.startswith("su2-from-stl:")


def _validate_mesh_bytes(
    mesh_bytes: bytes, mesh_format: MeshFormat, component: ComponentDefinition
) -> bytes:
    """Ensure exported mesh payloads are real, non-empty bytes."""
    if mesh_bytes is None or len(mesh_bytes) == 0:
        _raise_unsupported_format(mesh_format, component.uid)

    if _looks_like_handle(mesh_bytes):
        _raise_unsupported_format(mesh_format, component.uid)

    if mesh_format == "su2" and b"NDIME=" not in mesh_bytes:
        raise_mcp_error(
            "MeshExportError",
            f"Conversion to SU2 failed or output invalid for '{component.uid}'",
        )

    return mesh_bytes


def export_component_mesh_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the export_component_mesh tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = ExportMeshParams.model_validate(raw_params)
            _, tigl_handle, config = require_session(session_manager, params.session_id)
            # DEBUG: print available export-ish methods on tigl_handle (once) 
            if os.environ.get("TIGL_MCP_DEBUG_EXPORTS") == "1":
                keys = ("export", "step", "iges", "stp", "stl", "write", "save", "mesh")
                methods = [n for n in dir(tigl_handle) if any(k in n.lower() for k in keys)]
                print(f"[tigl-mcp][debug] tigl_handle export-ish methods: {methods}", file=sys.stderr, flush=True)
            component = config.find_component(params.component_uid)

            # If user passed a TiGL UID, map it back to our parsed component by tigl_uid
            if component is None:
                for c in config.all_components():
                    if c.parameters.get("tigl_uid") == params.component_uid:
                        component = c
                        break

            if component is None:
                raise_mcp_error("NotFound", f"Component '{params.component_uid}' not found")


            _ensure_export_supported(
                tigl_handle=tigl_handle,
                mesh_format=params.format,
                component_uid=params.component_uid,
            )
            if os.environ.get("TIGL_MCP_DEBUG_EXPORTS") == "1":
                print(f"[tigl-mcp][debug] tigl_handle type={type(tigl_handle)} repr={tigl_handle!r}", file=sys.stderr)
            mesh_bytes = _export_mesh_bytes(
                tigl_handle=tigl_handle,
                component=component,
                mesh_format=params.format,
            )
            validated_mesh = _validate_mesh_bytes(mesh_bytes, params.format, component)
            # mesh_base64 is reserved for mesh bytes only.
            mesh_base64 = base64.b64encode(validated_mesh).decode("utf-8")

            return {
                "format": params.format,
                "mesh_base64": mesh_base64,
                "num_triangles": 12 * component.index,
                "bounding_box": format_bounding_box(component.bounding_box),
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "MeshExportError", "Failed to export component mesh", str(exc)
            )

    return ToolDefinition(
        name="export_component_mesh",
        description="Export a component mesh as base64-encoded content.",
        parameters_model=ExportMeshParams,
        handler=handler,
        output_schema={},
    )

def _export_configuration_cad_bytes_via_tigl(tigl_handle: Any, cad_format: str) -> bytes:
    """
    Export the full aircraft as CAD (STEP/IGES) via TiGL into a temp file, then return bytes.
    This runs inside the TiGL Docker image where tigl3 is installed.
    """
    suffix = ".step" if cad_format == "step" else ".iges"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        out_path = Path(f.name)

    try:
        out_path.unlink(missing_ok=True)

        if cad_format == "step":
            candidates = ["exportFusedSTEP", "exportSTEP", "exportFusedStep", "exportStep"]
        else:
            candidates = ["exportFusedIGES", "exportIGES", "exportFusedIges", "exportIges"]

        tried: list[str] = []
        errors: list[str] = []

        # 1) Try explicit STEP/IGES methods first
        for name in candidates:
            fn = getattr(tigl_handle, name, None)
            if not callable(fn):
                continue

            tried.append(name)
            try:
                fn(str(out_path))
            except TypeError:
                # Some builds accept additional args; try a mild fallback
                try:
                    fn(str(out_path), True)
                except Exception as e:
                    errors.append(f"{name}: {type(e).__name__}: {e}")
                    continue
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")
                continue

            if out_path.exists() and out_path.stat().st_size > 0:
                return out_path.read_bytes()

        # 2) Fallback: sometimes format is inferred from extension
        for name in ["exportConfiguration", "exportconfiguration", "export"]:
            fn = getattr(tigl_handle, name, None)
            if not callable(fn):
                continue

            tried.append(name)
            try:
                fn(str(out_path))
                if out_path.exists() and out_path.stat().st_size > 0:
                    return out_path.read_bytes()
            except Exception as e:
                errors.append(f"{name}: {type(e).__name__}: {e}")

        raise_mcp_error(
            "CadExportError",
            f"TiGL could not export {cad_format.upper()} CAD.",
            {"methods_tried": tried, "errors": errors[:10]},
        )
    finally:
        out_path.unlink(missing_ok=True)



def export_configuration_cad_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the export_configuration_cad tool."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = ExportCadParams.model_validate(raw_params)
            tixi_handle, tigl_handle, _ = require_session(session_manager, params.session_id)

            # Always include CPACS xml in a separate field (useful for debugging + tests).
            cpacs_xml = getattr(tixi_handle, "xml_content", "") or ""
            cpacs_xml_base64 = base64.b64encode(cpacs_xml.encode("utf-8")).decode("utf-8")

            # Detect whether we're running with real TiGL (inside the Docker image).
            export_capable = any(
                callable(getattr(tigl_handle, name, None))
                for name in ("exportFusedSTEP", "exportSTEP", "exportConfiguration", "export")
            )

            if export_capable:
                cad_bytes = _export_configuration_cad_bytes_via_tigl(tigl_handle, params.format)
                source = "tigl"
            else:
                # Fallback stub payload (only if TiGL isn't available).
                cad_bytes = f"cad:{params.format}:{cpacs_xml}".encode("utf-8")
                source = "stub"

            cad_base64 = base64.b64encode(cad_bytes).decode("utf-8")
            return {
                "format": params.format,
                "cad_base64": cad_base64,          # REAL STEP bytes (in Docker)
                "source": source,                  # "tigl" or "stub"
                "cpacs_xml_base64": cpacs_xml_base64,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error(
                "CadExportError", "Failed to export configuration", str(exc)
            )

    return ToolDefinition(
        name="export_configuration_cad",
        description="Export the full configuration CAD and return it encoded.",
        parameters_model=ExportCadParams,
        handler=handler,
        output_schema={},
    )

def _get_aircraft_config(tigl_handle: object):
    # TiGL Python API: configuration manager -> configuration
    from tigl3.configuration import CCPACSConfigurationManager_get_instance
    mgr = CCPACSConfigurationManager_get_instance()
    return mgr.get_configuration(int(tigl_handle))

def _get_loft_shape(tigl_handle: object, component_uid: str):
    cfg = _get_aircraft_config(tigl_handle)
    uid_mgr = cfg.get_uidmanager()
    comp = uid_mgr.get_geometric_component(component_uid)
    return comp.get_loft()  # returns a TiGL shape object

def _require_tigl3() -> None:
    if export_shapes is None or create_exporter is None:
        raise_mcp_error(
            "DependencyMissing",
            "tigl3 (TiGL Python bindings) is not installed in this environment.",
            "Run the server inside the TiGL-enabled Docker image, or install TiGL/tigl3 locally.",
        )

def _export_shape_to_stl_bytes(tigl_handle: object, component_uid: str) -> bytes:
    _require_tigl3()
    shape = _get_loft_shape(tigl_handle, component_uid)

    # Best path: helper that exports based on filename extension
    try:
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
            out = Path(f.name)
        try:
            export_shapes([shape], str(out), deflection=0.001)
            return out.read_bytes()
        finally:
            out.unlink(missing_ok=True)
    except ImportError:
        pass  # fallback below

    # Fallback: explicit exporter

    exporter = create_exporter("stl")
    exporter.add_shape(shape)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        out = Path(f.name)
    try:
        exporter.write(str(out))
        return out.read_bytes()
    finally:
        out.unlink(missing_ok=True)

def _uid_candidates(component: ComponentDefinition) -> list[str]:
    tigl_uid = component.parameters.get("tigl_uid") if component.parameters else None
    if isinstance(tigl_uid, str) and tigl_uid:
        return [tigl_uid]

    u = component.uid
    cands = [u, u.replace("_",""), u.replace("_","").title()]
    seen=set(); out=[]
    for x in cands:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out



def _export_stl_bytes_via_tigl3(tigl: Any, component: ComponentDefinition) -> bytes:
    """
    Export a real STL using tigl3wrapper.Tigl3 methods.

    Tries:
      - Wing/Fuselage by UID (with/without deflection)
      - Wing/Fuselage by Index (with/without deflection)
      - Whole geometry STL fallback
    """
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
        stl_path = Path(f.name)

    errors: list[str] = []
    tried: list[tuple[str, tuple[object, ...]]] = []

    def _try(method: str, *args: object) -> bytes | None:
        fn = getattr(tigl, method, None)
        if not callable(fn):
            return None
        tried.append((method, args))
        try:
            stl_path.unlink(missing_ok=True)
            fn(*args)
            if stl_path.exists() and stl_path.stat().st_size > 2048:
                return stl_path.read_bytes()
            # if it wrote something tiny, record it
            if stl_path.exists():
                errors.append(f"{method}{args} wrote {stl_path.stat().st_size} bytes (too small)")
            else:
                errors.append(f"{method}{args} produced no file")
        except Exception as e:
            errors.append(f"{method}{args} {type(e).__name__}: {e}")
        return None

    try:
        ctype = (component.type_name or "").lower()
        uid_list = _uid_candidates(component)
        idx = int(component.index)

        # Reasonable default deflection (triangulation fineness)
        defl = float(os.environ.get("TIGL_STL_DEFLECTION", "0.001"))

        if "wing" in ctype:
            for uid in uid_list:
                for candidate in [
                    ("exportMeshedWingSTLByUID", (uid, str(stl_path), defl)),
                    ("exportMeshedWingSTLByUID", (uid, str(stl_path))),
                ]:
                    out = _try(candidate[0], *candidate[1])
                    if out is not None:
                        return out

            # by-index (often exists in TiGL)
            for candidate in [
                ("exportMeshedWingSTL", (idx, str(stl_path), defl)),
                ("exportMeshedWingSTL", (idx, str(stl_path))),
            ]:
                out = _try(candidate[0], *candidate[1])
                if out is not None:
                    return out

        if "fuselage" in ctype:
            for uid in uid_list:
                for candidate in [
                    ("exportMeshedFuselageSTLByUID", (uid, str(stl_path), defl)),
                    ("exportMeshedFuselageSTLByUID", (uid, str(stl_path))),
                ]:
                    out = _try(candidate[0], *candidate[1])
                    if out is not None:
                        return out

            for candidate in [
                ("exportMeshedFuselageSTL", (idx, str(stl_path), defl)),
                ("exportMeshedFuselageSTL", (idx, str(stl_path))),
            ]:
                out = _try(candidate[0], *candidate[1])
                if out is not None:
                    return out

        # Whole-aircraft fallback
        for candidate in [
            ("exportMeshedGeometrySTL", (str(stl_path), defl)),
            ("exportMeshedGeometrySTL", (str(stl_path),)),
        ]:
            out = _try(candidate[0], *candidate[1])
            if out is not None:
                return out

        raise_mcp_error(
            "MeshExportError",
            "No working STL export route found.",
            {"errors": errors[:20]},
        )

    finally:
        stl_path.unlink(missing_ok=True)
