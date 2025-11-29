"""CLI-level coverage for the FastMCP server wrapper."""

from __future__ import annotations

import pytest

from tigl_mcp_server import main as server_main


class _DummyApp:
    """Shim FastMCP app to capture run invocations without network I/O."""

    def __init__(self) -> None:
        self.run_calls: list[dict[str, object]] = []

    def add_tool(self, _: object) -> None:  # pragma: no cover - not used directly
        return

    def run(
        self, *, transport: str, **kwargs: object
    ) -> None:  # pragma: no cover - exercised via main
        self.run_calls.append({"transport": transport, **kwargs})


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
