"""Sphinx configuration for the `tigl-mcp` documentation."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

project = "tigl-mcp"
author = "TiGL Team"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]
autodoc_mock_imports = [
    "fastmcp",
    "fastmcp.tools",
    "fastmcp.tools.tool",
    "mcp",
    "meshio",
]
nitpick_ignore = [
    ("py:class", "argparse.ArgumentParser"),
    ("py:class", "collections.abc.Callable"),
    ("py:class", "collections.abc.Iterable"),
    ("py:class", "collections.abc.Sequence"),
    ("py:class", "tigl_mcp_server.errors.MCPErrorPayload"),
]
templates_path: list[str] = []
exclude_patterns = ["_build"]
html_theme = "alabaster"
