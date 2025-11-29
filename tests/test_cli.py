"""CLI behavior smoke tests."""

from __future__ import annotations

import json
from typing import List

from tigl_mcp import cli


def test_cli_outputs_dummy_tool(monkeypatch, capsys) -> None:  # type: ignore[annotation-unchecked]
    """Running the CLI without flags should execute the dummy tool."""

    # Arrange
    argv: List[str] = []

    # Act
    exit_code = cli.main(argv)

    # Assert
    assert exit_code == 0
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed["name"] == "dummy"
    assert parsed["payload"]["status"] == "ok"


def test_cli_catalog_flag(monkeypatch, capsys) -> None:  # type: ignore[annotation-unchecked]
    """Catalog flag should print tool discovery metadata."""

    # Arrange
    argv: List[str] = ["--catalog"]

    # Act
    exit_code = cli.main(argv)

    # Assert
    assert exit_code == 0
    captured = capsys.readouterr()
    catalog = json.loads(captured.out)
    assert "dummy" in catalog
    assert catalog["dummy"]["description"]
