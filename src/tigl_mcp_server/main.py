"""Entry point for the TiGL MCP server tool registry."""

from __future__ import annotations

import argparse
import json

from tigl_mcp.server import MCPServer
from tigl_mcp_server.session_manager import session_manager
from tigl_mcp_server.tools import build_tools


def main() -> None:
    """Register tools and print a JSON catalog."""
    parser = argparse.ArgumentParser(description="TiGL MCP server")
    parser.add_argument("--catalog", action="store_true", help="Print the tool catalog")
    args = parser.parse_args()

    server = MCPServer()
    server.register_tools(*build_tools(session_manager))
    if args.catalog:
        print(json.dumps(server.to_catalog(), indent=2))
    else:
        print(json.dumps({"tools": server.available_tools()}))


if __name__ == "__main__":
    main()
