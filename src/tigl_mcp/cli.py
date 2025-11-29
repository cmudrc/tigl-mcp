"""Command-line interface for the TiGL MCP scaffold."""

from __future__ import annotations

import argparse
import json

from tigl_mcp.server import MCPServer
from tigl_mcp.tools import register_dummy_tool


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(description="Run the TiGL MCP scaffold.")
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="Print the available tool catalog as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    server = MCPServer()
    server.register_tool(register_dummy_tool())

    if args.catalog:
        catalog = server.to_catalog()
        print(json.dumps(catalog, indent=2))
        return 0

    result = server.run_tool("dummy")
    print(result.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
