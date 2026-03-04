"""Repository-level checks for docs scaffolding and generated indexes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_script(relative_path: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a repo script from the repository root."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, relative_path, *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_required_docs_files_exist() -> None:
    """The new Sphinx entrypoints are tracked in the repository."""
    required_paths = [
        REPO_ROOT / "docs" / "index.rst",
        REPO_ROOT / "docs" / "quickstart.rst",
        REPO_ROOT / "docs" / "api.rst",
        REPO_ROOT / "docs" / "reference" / "index.rst",
        REPO_ROOT / "docs" / "examples" / "index.rst",
        REPO_ROOT / "docs" / "examples" / "generated_examples.rst",
    ]

    for path in required_paths:
        assert path.exists(), f"Missing required docs file: {path}"


def test_generated_example_docs_are_current() -> None:
    """The generated examples fragment matches the checked-in example set."""
    completed = _run_script("scripts/generate_example_docs.py", "--check")
    assert completed.returncode == 0, completed.stderr


def test_docs_consistency_script_passes() -> None:
    """The lightweight docs consistency check succeeds."""
    completed = _run_script("scripts/check_docs_consistency.py")
    assert completed.returncode == 0, completed.stderr
