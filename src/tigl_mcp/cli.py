"""Command-line interface for the TiGL MCP scaffold."""

from __future__ import annotations

import argparse

from tigl_mcp.server import MCPServer
from tigl_mcp.tools import register_dummy_tool


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    return argparse.ArgumentParser(description="Run the TiGL MCP scaffold.")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI."""
    parser = build_parser()
    parser.parse_args(argv)

    server = MCPServer()
    server.register_tool(register_dummy_tool())

    result = server.run_tool("dummy")
    print(result.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
