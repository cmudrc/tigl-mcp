"""CLI behavior smoke tests."""

from __future__ import annotations

import json

from pytest import CaptureFixture

from tigl_mcp import cli


def test_cli_outputs_dummy_tool(capsys: CaptureFixture[str]) -> None:
    """Running the CLI without flags should execute the dummy tool."""
    # Arrange
    argv: list[str] = []

    # Act
    exit_code = cli.main(argv)

    # Assert
    assert exit_code == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["name"] == "dummy"
    assert parsed["payload"]["status"] == "ok"
