# tigl-mcp

A lightweight scaffold for a Model Context Protocol (MCP) server focused on TiGL. The
project now exposes its core tooling primitives from the consolidated
`tigl_mcp_server` package, which also provides the `tigl-mcp-server` CLI and
`python -m tigl_mcp_server` entry point for running the server. TiGL/CPACS
geometry is exposed through JSON-schema-described tools.

## Features

- FastMCP-powered MCP server with stdio and HTTP transports
- Pydantic-backed parameter validation via reusable tool definitions
- TiGL/CPACS-aware tool implementations backed by a reusable `SessionManager`
- JSON-serializable tool definitions for the full geometry workflow
- Pytest-based test suite with coverage reporting
- Component mesh export supporting STL/VTP/Collada plus SU2 via TiGL or STL
  conversion

## Getting started

Install the project in editable mode along with the development dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

Run the test suite to verify the scaffold:

```bash
pytest
```

Start the FastMCP server over stdio or HTTP transports:

```bash
tigl-mcp-server --transport stdio

# or expose websocket/SSE discovery endpoints over HTTP
tigl-mcp-server --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

## Docker

Build the image (includes TiGL, Gmsh, SU2):

```bash
docker build -t tigl-mcp:dev .
```

**Apple Silicon (M1/M2/M3):** The TiGL/TIXI packages from the `dlr-sc` channel are only built for `linux/amd64`. Build for that platform so the image works (Docker will run it under emulation):

```bash
docker build --platform linux/amd64 -t tigl-mcp:dev .
```

To run SU2 on a folder that contains your mesh and config:

```bash
docker run --rm -v /path/to/out_step:/work tigl-mcp:dev \
  bash -lc "cd /work && SU2_CFD euler_smoke.cfg"
```

## Examples

The `examples/` directory contains standalone scripts that demonstrate the MCP
workflow:

- `mcp_export_step.py` — export the full aircraft as STEP via the MCP HTTP
  endpoint.
- `mcp_export_stl.py` — export a single component mesh as STL via the MCP HTTP
  endpoint.

## Full pipeline (TiGL → SU2 → pyCycle)

This server is the first stage of an automated aircraft analysis pipeline:

```
CPACS XML → [TiGL MCP] → STEP → [Gmsh] → Mesh → [SU2] → CL/CD → [pyCycle] → TSFC
```

The pipeline is driven by a `pipeline_config.yaml` that controls flight conditions, mesh quality, CFD settings, and engine parameters. See [su2-mcp](https://github.com/cmudrc/su2-mcp) and [pycycle-mcp](https://github.com/cmudrc/pycycle-mcp) for the downstream servers.

### TiGL-specific notes

- **STEP export** uses OpenCASCADE (`ShapeFix_Shell` → `BRepBuilderAPI_MakeSolid` → `BRepAlgoAPI_Fuse`) to produce watertight `MANIFOLD_SOLID_BREP` geometry suitable for volume meshing.
- **Symmetric mirroring** is handled automatically — `get_mirrored_loft()` is called for wings and fuselages so the exported STEP contains the full aircraft.
- STEP deflection tolerance is hardcoded at 0.001 (model units). This is tight enough that the geometry itself is smooth; any visual coarseness comes from the downstream mesh density.

### System-level dependencies

TiGL and its dependencies cannot be pip-installed. Use conda:

```bash
conda create -n tigl -c dlr-sc -c conda-forge python=3.11 tigl3 pythonocc-core
conda activate tigl
pip install -e .
```

Or use the Docker image (`docker build -t tigl-mcp:dev .`), which bundles TiGL, Gmsh, and SU2.

## Contributing

- Keep modules single-purpose and favor pure functions.
- Use the provided formatting and linting configuration (`black`, `ruff`, `mypy`).
- Add tests for new behavior and prefer clear Arrange-Act-Assert structure.
