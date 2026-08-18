# tigl-mcp

[![CI](https://github.com/cmudrc/tigl-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/cmudrc/tigl-mcp/actions/workflows/ci.yml)
[![Docs](https://github.com/cmudrc/tigl-mcp/actions/workflows/docs-pages.yml/badge.svg)](https://github.com/cmudrc/tigl-mcp/actions/workflows/docs-pages.yml)
[![Examples](https://github.com/cmudrc/tigl-mcp/actions/workflows/examples.yml/badge.svg)](https://github.com/cmudrc/tigl-mcp/actions/workflows/examples.yml)

`tigl-mcp` is a lightweight Model Context Protocol server for CPACS-oriented
TiGL workflows. The current implementation focuses on deterministic,
JSON-friendly tooling backed by stubbed CPACS/TiGL behavior so local
development, tests, and docs stay stable without native geometry runtimes.

## Overview

The project currently provides:

- A FastMCP-powered server with stdio and HTTP-compatible transports
- A curated set of CPACS lifecycle, inspection, export, sampling, and parameter
  tools
- Pydantic-backed tool validation with structured MCP error payloads
- Deterministic CPACS/TiGL stand-ins for stable local development and CI

## Quickstart

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
make dev
make test
make ci
```

Start the server over stdio:

```bash
tigl-mcp --transport stdio
```

Inspect the non-blocking HTTP transport configuration example:

```bash
PYTHONPATH=src python3 examples/server/http_launch_config.py
```

## Examples

The examples are deterministic and aligned with the current stub-backed
implementation.

- Examples index: [`examples/README.md`](examples/README.md)
- Tool discovery: [`examples/client/tool_discovery.py`](examples/client/tool_discovery.py)
- Session lifecycle: [`examples/cpacs/session_lifecycle.py`](examples/cpacs/session_lifecycle.py)
- Export snapshot: [`examples/cpacs/export_snapshot.py`](examples/cpacs/export_snapshot.py)

## Docs

- Docs source: [`docs/index.rst`](docs/index.rst)
- Published docs: <https://cmudrc.github.io/tigl-mcp/>

Build the docs locally with:

```bash
make docs
```

## Current Capability Boundaries

This is the authoritative statement of which paths run real TiGL and which do
not. Nothing here estimates geometry.

**Real TiGL, always.** CAD export (`export_configuration_cad`, STEP and IGES)
and mesh export (`export_component_mesh`) drive the real TiGL library, either
through native `tigl3`/`tixi3` bindings or through the `tigl-mcp:dev` Docker
image. The route actually taken is recorded in CPACS as `stepExportSource`, so
exported geometry is traceable. On the D150 this produces a 3.2 MB STEP file
and per-component surface meshes of a few thousand triangles.

**Read from the CPACS file, so always available.** Component UIDs, names,
symmetry flags, wing/fuselage/rotor/engine counts, per-component section and
segment counts, and the reference area and length. These are values the file
states directly.

**Requires a real kernel, and reports `GeometryUnavailable` without one.**
Bounding boxes, wing span and area, aspect ratio, MAC, fuselage length, surface
sampling, and plane/component intersection. Deriving any of these means
evaluating profile geometry through the CPACS positioning and transformation
chain, which is what TiGL is for. When no kernel is reachable these tools raise
a structured error naming the missing dependency. They do not return an
estimate.

> Until 2026-08-15 several of these returned values derived from a component's
> index in an array — a wing's bounding box was literally its position in the
> list. Those were removed, along with a synthetic single-triangle mesh and a
> CAD "export" that returned the CPACS text relabelled. If you are reading
> older notes or output that mention stub geometry, they predate this.

## Shared-CPACS Integration

This MCP includes a **CPACS adapter** (`src/tigl_mcp/cpacs_adapter.py`) that
bridges TiGL to the shared-CPACS aircraft analysis pipeline.

### What it does

The adapter reads CPACS geometry (wings, fuselages, profiles) and writes
analysis results — component counts, per-component section and segment counts,
and STEP export metadata — into `//analysisResults/tigl`. A `boundingBox`
element is written only when a real geometry kernel supplied one, and is
omitted otherwise.

| Direction | XPath |
|-----------|-------|
| **Reads** | `.//vehicles/aircraft/model`, `.//vehicles/profiles` |
| **Writes** | `.//vehicles/aircraft/model/analysisResults/tigl` |

### Running as part of the pipeline

```bash
# As part of the full 4-MCP pipeline (with SU2, pyCycle, Mission)
python pipeline/shared_cpacs_orchestrator.py D150_v30.xml --mcps tigl su2 pycycle mission

# TiGL only
python pipeline/shared_cpacs_orchestrator.py D150_v30.xml --mcps tigl
```

See [cmudrc/aircraft-analysis](https://github.com/cmudrc/aircraft-analysis) for
full pipeline documentation, versioning details, and installation instructions.

### Related MCP servers

| MCP | Repository |
|-----|-----------|
| SU2 (CFD aerodynamics) | [cmudrc/su2-mcp](https://github.com/cmudrc/su2-mcp) |
| pyCycle (engine cycle) | [cmudrc/pycycle-mcp](https://github.com/cmudrc/pycycle-mcp) |
| Mission, segment/Breguet | [cmudrc/nseg-mcp](https://github.com/cmudrc/nseg-mcp) |
| Mission, trajectory-level | [cmudrc/aviary-cpacs-mcp](https://github.com/cmudrc/aviary-cpacs-mcp) |

## Contributing

Contribution guidelines live in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Maintainers

Mayank Dixit ([@Kugel-Blitz-13](https://github.com/Kugel-Blitz-13)), Carnegie
Mellon University — mayankd@cmu.edu
Christopher McComb, Carnegie Mellon University — Design Research Collective
