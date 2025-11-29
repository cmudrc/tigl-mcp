# tigl-mcp

A lightweight scaffold for a Model Context Protocol (MCP) server focused on TiGL. The
current implementation provides an in-memory tool registry, a dummy tool for smoke
testing, and a small command-line interface.

## Features

- In-memory `MCPServer` for registering and dispatching tools
- Pydantic-backed parameter validation via reusable tool definitions
- Dummy tool to verify the server pipeline end to end
- CLI for quick manual checks and catalog export
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

## Contributing

- Keep modules single-purpose and favor pure functions.
- Use the provided formatting and linting configuration (`black`, `ruff`, `mypy`).
- Add tests for new behavior and prefer clear Arrange-Act-Assert structure.
