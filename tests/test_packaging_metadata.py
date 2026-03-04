"""Checks for packaging metadata and developer-facing repository contracts."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, object]:
    """Load and parse the repository pyproject file."""
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_project_urls_and_cli_entrypoint_are_declared() -> None:
    """The package metadata exposes repo links and the CLI entrypoint."""
    project = _pyproject()["project"]

    assert project["requires-python"] == ">=3.11"
    assert project["scripts"]["tigl-mcp-server"] == "tigl_mcp_server.main:main"
    assert "Documentation" in project["urls"]
    assert "Repository" in project["urls"]
    assert "Issues" in project["urls"]


def test_dev_dependencies_include_docs_and_release_tooling() -> None:
    """The dev extra includes tooling required by the new repo scaffolding."""
    dev_dependencies = _pyproject()["project"]["optional-dependencies"]["dev"]

    assert any(dep.startswith("sphinx") for dep in dev_dependencies)
    assert any(dep.startswith("build") for dep in dev_dependencies)
    assert any(dep.startswith("twine") for dep in dev_dependencies)
    assert any(dep.startswith("pre-commit") for dep in dev_dependencies)


def test_makefile_exposes_required_targets() -> None:
    """The Makefile defines the new top-level developer workflow targets."""
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    for target in [
        "dev:",
        "test:",
        "qa:",
        "coverage:",
        "examples-smoke:",
        "examples-test:",
        "docs-build:",
        "docs-check:",
        "docs-linkcheck:",
        "release-check:",
        "ci:",
    ]:
        assert target in makefile
