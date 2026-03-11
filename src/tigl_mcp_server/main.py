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
    sub = parser.add_subparsers(dest="command")

    # --- serve (default) ---
    serve = sub.add_parser("serve", help="Start the MCP server (default)")
    serve.add_argument(
        "--transport",
        choices=("stdio", "http", "sse", "streamable-http"),
        default="stdio",
        help=(
            "Transport for serving MCP (stdio for CLI integration, HTTP for "
            "websocket/SSE endpoints)."
        ),
    )
    serve.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind for HTTP-compatible transports (default: 0.0.0.0)",
    )
    serve.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind for HTTP-compatible transports (default: 8000)",
    )
    serve.add_argument(
        "--path",
        help=(
            "Path to mount the HTTP endpoint (defaults to FastMCP's protocol-specific"
            " path)."
        ),
    )

    # --- check-runtime ---
    sub.add_parser(
        "check-runtime",
        help="Verify that TiGL, TiXI, OpenCASCADE, and Gmsh are available",
    )

    # Keep backwards compat: bare flags on the top-level parser for the
    # common case where users run ``tigl-mcp-server --transport http``.
    parser.add_argument("--transport", dest="_compat_transport", default=None,
                        choices=("stdio", "http", "sse", "streamable-http"),
                        help=argparse.SUPPRESS)
    parser.add_argument("--host", dest="_compat_host", default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--port", dest="_compat_port", type=int, default=None,
                        help=argparse.SUPPRESS)
    parser.add_argument("--path", dest="_compat_path", default=None,
                        help=argparse.SUPPRESS)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Register tools and start the FastMCP server."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle check-runtime subcommand
    if args.command == "check-runtime":
        from tigl_mcp_server.runtime_check import print_runtime_report

        print_runtime_report()
        return 0

    # Resolve transport args: prefer subcommand attrs, fall back to compat flags
    transport = getattr(args, "transport", None) or args._compat_transport or "stdio"
    host = getattr(args, "host", None) or args._compat_host or "0.0.0.0"
    port = getattr(args, "port", None) or args._compat_port or 8000
    path = getattr(args, "path", None) or args._compat_path

    app, _tool_definitions = build_fastmcp_app(session_manager)
    transport_kwargs: dict[str, Any] = {}
    if transport in {"http", "sse", "streamable-http"}:
        transport_kwargs["host"] = host
        transport_kwargs["port"] = port
        if path is not None:
            transport_kwargs["path"] = path

    # IMPORTANT: keep stdio clean (no banner, minimal logs)
    if transport == "stdio":
        transport_kwargs["show_banner"] = False
        transport_kwargs["log_level"] = "ERROR"

    app.run(transport=transport, **transport_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
