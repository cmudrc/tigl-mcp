"""Sphinx configuration for the `tigl-mcp` documentation."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from sphinx.application import Sphinx

autoclass_content = "both"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

project = "tigl-mcp"
copyright = "2026, tigl-mcp contributors"
author = "TiGL Team"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
autodoc_typehints = "none"
autosummary_generate = True
autosummary_imported_members = True
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
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

if os.environ.get("READTHEDOCS") == "True":
    html_theme = "sphinx_rtd_theme"
else:
    try:
        import sphinx_rtd_theme  # noqa: F401

        html_theme = "sphinx_rtd_theme"
    except ImportError:
        html_theme = "alabaster"

html_static_path = ["_static"]
html_logo = "drc.png"
html_theme_options = {
    "logo_only": True,
}

_VIEWPORT_META_RE = re.compile(r'<meta name="viewport"[^>]*>', re.IGNORECASE)


def _dedupe_viewport_meta(
    app: object,
    pagename: str,
    templatename: str,
    context: dict[str, object],
    doctree: object,
) -> None:
    """Keep one viewport tag by removing duplicate entries."""
    del app, pagename, templatename, doctree
    metatags = context.get("metatags")
    if isinstance(metatags, str):
        context["metatags"] = _VIEWPORT_META_RE.sub("", metatags)


def setup(app: Sphinx) -> None:
    """Register build-time hooks."""
    app.connect("html-page-context", _dedupe_viewport_meta)
