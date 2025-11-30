# tigl-mcp

A lightweight scaffold for a Model Context Protocol (MCP) server focused on TiGL. The
project now includes a standalone `tigl_mcp_server` package that exposes TiGL/CPACS
geometry through JSON-schema-described tools.

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

## Contributing

- Keep modules single-purpose and favor pure functions.
- Use the provided formatting and linting configuration (`black`, `ruff`, `mypy`).
- Add tests for new behavior and prefer clear Arrange-Act-Assert structure.
