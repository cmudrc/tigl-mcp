"""CLI contract tests for the TiGL MCP server entrypoints."""

from __future__ import annotations

import pytest

from tigl_mcp_server import main as server_main


class _DummyApp:
    """Shim FastMCP app to capture run invocations without network I/O."""

    def __init__(self) -> None:
        self.run_calls: list[dict[str, object]] = []

    def add_tool(self, _: object) -> None:  # pragma: no cover - compatibility shim
        return

    def run(self, *, transport: str, **kwargs: object) -> None:
        """Capture transport arguments passed by the CLI."""
        self.run_calls.append({"transport": transport, **kwargs})


def test_build_parser_defaults_to_stdio_transport() -> None:
    """The CLI defaults to the local stdio transport."""
    parser = server_main.build_parser()
    args = parser.parse_args([])

    assert args.transport == "stdio"
    assert args.host == "0.0.0.0"
    assert args.port == 8000
    assert args.path is None


def test_main_runs_fastmcp_with_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() delegates to FastMCP.run with the provided transport settings."""
    dummy_app = _DummyApp()
    monkeypatch.setattr(
        server_main,
        "build_fastmcp_app",
        lambda _session_manager: (dummy_app, []),
    )

    exit_code = server_main.main(
        [
            "--transport",
            "http",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "--path",
            "/mcp",
        ]
    )

    assert exit_code == 0
    assert dummy_app.run_calls == [
        {"transport": "http", "host": "127.0.0.1", "port": 8080, "path": "/mcp"}
    ]
