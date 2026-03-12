"""Runtime validation for TiGL/TiXI native dependencies."""

from __future__ import annotations

import shutil
import sys

CONDA_INSTALL_CMD = (
    "conda install -c dlr-sc -c conda-forge tigl3 tixi3 python-tigl3 python-tixi3"
)

DOCKER_BUILD_CMD = "docker build -t tigl-mcp:dev ."

INSTALL_GUIDE = f"""\
TiGL/TiXI native bindings are not available in this Python environment.

To install, choose one of the following options:

  1. Conda (recommended):
     {CONDA_INSTALL_CMD}

  2. Conda environment file (ships with this repo):
     conda env create -f environment.yml
     conda activate tigl-mcp

  3. Docker (includes TiGL + Gmsh + SU2):
     {DOCKER_BUILD_CMD}

  4. Pre-built binaries from DLR:
     https://github.com/DLR-SC/tigl/releases

The server will still start in stub mode (synthetic geometry) without
these bindings, but real STEP/STL export requires the native runtime.
"""


def check_tigl_runtime() -> dict[str, object]:
    """Probe the environment for TiGL and TiXI availability.

    Returns a dict suitable for printing or returning as a tool response.
    """
    results: dict[str, object] = {
        "python": sys.version,
        "platform": sys.platform,
    }

    # TiXI
    try:
        from tixi3 import tixi3wrapper  # type: ignore[import-untyped]

        tixi_h = tixi3wrapper.Tixi3()
        ver = getattr(tixi_h, "version", "unknown")
        results["tixi3"] = {"available": True, "version": ver}
    except Exception as exc:
        results["tixi3"] = {"available": False, "error": str(exc)}

    # TiGL
    try:
        from tigl3 import tigl3wrapper  # type: ignore[import-untyped]

        results["tigl3"] = {"available": True, "module": tigl3wrapper.__name__}
    except Exception as exc:
        results["tigl3"] = {"available": False, "error": str(exc)}

    # OpenCASCADE (used for watertight STEP export)
    try:
        from OCC.Core.BRepBuilderAPI import (
            BRepBuilderAPI_MakeSolid,  # type: ignore[import-untyped]  # noqa: F401
        )

        results["opencascade"] = {"available": True}
    except Exception as exc:
        results["opencascade"] = {"available": False, "error": str(exc)}

    # Gmsh (used for meshing in the pipeline)
    gmsh_bin = shutil.which("gmsh")
    try:
        import gmsh as _gmsh  # type: ignore[import-untyped]  # noqa: F401

        results["gmsh"] = {
            "available": True,
            "python_api": True,
            "cli": gmsh_bin or "not on PATH",
        }
    except Exception:
        results["gmsh"] = {
            "available": gmsh_bin is not None,
            "python_api": False,
            "cli": gmsh_bin or "not on PATH",
        }

    all_ok = all(
        isinstance(v, dict) and v.get("available", False)
        for v in results.values()
        if isinstance(v, dict)
    )
    results["all_ok"] = all_ok

    return results


def print_runtime_report() -> None:
    """Print a human-readable runtime diagnostics report."""
    report = check_tigl_runtime()

    print("=" * 60)
    print("  TiGL MCP Runtime Check")
    print("=" * 60)
    print(f"  Python:      {report['python']}")
    print(f"  Platform:    {report['platform']}")
    print()

    for name in ("tixi3", "tigl3", "opencascade", "gmsh"):
        info = report.get(name, {})
        if not isinstance(info, dict):
            continue
        ok = info.get("available", False)
        status = "OK" if ok else "MISSING"
        marker = "+" if ok else "x"
        line = f"  [{marker}] {name:15s} {status}"
        if not ok and "error" in info:
            line += f"  ({info['error'][:80]})"
        if ok and "version" in info:
            line += f"  (v{info['version']})"
        if "cli" in info:
            line += f"  [cli: {info['cli']}]"
        print(line)

    print()
    if report.get("all_ok"):
        print("  All dependencies found. Full TiGL geometry export is available.")
    else:
        print("  Some dependencies are missing. The server will run in stub mode.")
        print()
        print(INSTALL_GUIDE)

    print("=" * 60)
