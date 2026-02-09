"""Entry point for the TiGL MCP FastMCP server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from tigl_mcp_server.fastmcp_adapter import build_fastmcp_app
from tigl_mcp_server.session_manager import session_manager


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the FastMCP server CLI."""
    parser = argparse.ArgumentParser(description="TiGL MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse", "streamable-http"),
        default="stdio",
        help=(
            "Transport for serving MCP (stdio for CLI integration, HTTP for "
            "websocket/SSE endpoints)."
        ),
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind for HTTP-compatible transports (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for HTTP-compatible transports (default: 8000)",
    )
    parser.add_argument(
        "--path",
        help=(
            "Path to mount the HTTP endpoint (defaults to FastMCP's protocol-specific"
            " path)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Register tools and start the FastMCP server."""
    parser = build_parser()
    args = parser.parse_args(argv)

    app, _tool_definitions = build_fastmcp_app(session_manager)
    transport_kwargs: dict[str, Any] = {}
    if args.transport in {"http", "sse", "streamable-http"}:
        transport_kwargs["host"] = args.host
        transport_kwargs["port"] = args.port
        if args.path is not None:
            transport_kwargs["path"] = args.path

    # IMPORTANT: keep stdio clean (no banner, minimal logs)
    if args.transport == "stdio":
        transport_kwargs["show_banner"] = False
        transport_kwargs["log_level"] = "ERROR"

    app.run(transport=args.transport, **transport_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
