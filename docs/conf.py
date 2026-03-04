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
templates_path: list[str] = []
exclude_patterns = ["_build"]
html_theme = "alabaster"
