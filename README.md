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

- The default tests and examples target the deterministic stand-ins in
  `tigl_mcp.cpacs_stubs`.
- Tool names, schemas, and JSON payload shapes are stable.
- Geometry values are intentionally simplified; they reflect the current stub
  contract rather than full native TiGL fidelity.

## Shared-CPACS Integration

This MCP includes a **CPACS adapter** (`src/tigl_mcp/cpacs_adapter.py`) that
bridges TiGL to the shared-CPACS aircraft analysis pipeline.

### What it does

The adapter reads CPACS geometry (wings, fuselages, profiles) and writes
analysis results — component counts, bounding boxes, and STEP export metadata
— into `//analysisResults/tigl`.

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
| Mission (trajectory/fuel) | [cmudrc/mission-mcp](https://github.com/cmudrc/mission-mcp) |

## Contributing

Contribution guidelines live in [`CONTRIBUTING.md`](CONTRIBUTING.md).
