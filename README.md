# tigl-mcp

A lightweight scaffold for a Model Context Protocol (MCP) server focused on TiGL. The
project now includes a standalone `tigl_mcp_server` package that exposes TiGL/CPACS
geometry through JSON-schema-described tools, alongside the original minimal MCP
registry used for validation and catalog export.

## Features

- In-memory `MCPServer` for registering and dispatching tools
- Pydantic-backed parameter validation via reusable tool definitions
- TiGL/CPACS-aware tool implementations backed by a reusable `SessionManager`
- JSON-serializable tool definitions for the full geometry workflow
- Dummy tool to verify the legacy MCP pipeline end to end
- CLI for quick manual checks and catalog export (`python -m tigl_mcp`)
- Server catalog CLI for the new toolset (`python -m tigl_mcp_server --catalog`)
- Pytest-based test suite with coverage reporting

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

Inspect the available tools from the command line:

```bash
python -m tigl_mcp.cli --catalog
```

Running without flags executes the dummy tool and prints a JSON payload.

Inspect the TiGL MCP server tool catalog:

```bash
python -m tigl_mcp_server --catalog
```

The catalog is derived from pydantic schemas, and every tool returns structured JSON.

## Contributing

- Keep modules single-purpose and favor pure functions.
- Use the provided formatting and linting configuration (`black`, `ruff`, `mypy`).
- Add tests for new behavior and prefer clear Arrange-Act-Assert structure.
