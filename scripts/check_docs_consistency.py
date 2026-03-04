"""Validate that the docs tree contains the expected structural entrypoints."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = [
    REPO_ROOT / "docs" / "index.rst",
    REPO_ROOT / "docs" / "quickstart.rst",
    REPO_ROOT / "docs" / "api.rst",
    REPO_ROOT / "docs" / "reference" / "index.rst",
    REPO_ROOT / "docs" / "examples" / "index.rst",
    REPO_ROOT / "docs" / "examples" / "generated_examples.rst",
]


def _require_contains(path: Path, expected: str) -> None:
    """Require a file to contain a specific substring."""
    contents = path.read_text(encoding="utf-8")
    if expected not in contents:
        raise SystemExit(f"{path} is missing required text: {expected!r}")


def main() -> int:
    """Run lightweight structural checks against the docs tree."""
    missing = [str(path) for path in REQUIRED_DOCS if not path.exists()]
    if missing:
        raise SystemExit(f"Missing required docs files: {', '.join(missing)}")

    _require_contains(REPO_ROOT / "docs" / "index.rst", "reference/index")
    _require_contains(REPO_ROOT / "docs" / "index.rst", "examples/index")
    _require_contains(
        REPO_ROOT / "docs" / "examples" / "index.rst",
        "generated_examples",
    )
    _require_contains(
        REPO_ROOT / "docs" / "examples" / "generated_examples.rst",
        "examples/client/tool_discovery.py",
    )

    print("Docs structure is consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
