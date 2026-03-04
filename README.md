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
tigl-mcp-server --transport stdio
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
  `tigl_mcp_server.cpacs_stubs`.
- Tool names, schemas, and JSON payload shapes are stable.
- Geometry values are intentionally simplified; they reflect the current stub
  contract rather than full native TiGL fidelity.

## Contributing

Contribution guidelines live in [`CONTRIBUTING.md`](CONTRIBUTING.md).
