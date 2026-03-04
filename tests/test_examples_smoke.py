"""Deterministic example smoke tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.examples_smoke


def _run_example(relative_path: str) -> subprocess.CompletedProcess[str]:
    """Execute an example script from the repository root."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, relative_path],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_tool_discovery_example_runs() -> None:
    """The in-process tool discovery example lists the registered tools."""
    completed = _run_example("examples/client/tool_discovery.py")
    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)
    assert payload["tool_count"] >= 10
    assert "open_cpacs" in payload["tool_names"]


def test_session_lifecycle_example_runs() -> None:
    """The session lifecycle example opens and closes a stub-backed session."""
    completed = _run_example("examples/cpacs/session_lifecycle.py")
    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)
    assert payload["session_opened"] is True
    assert payload["session_closed"] is True
    assert payload["wing_ids"] == ["W1"]


@pytest.mark.examples_full
def test_export_snapshot_example_runs() -> None:
    """The export example returns stable stub payload metadata."""
    completed = _run_example("examples/cpacs/export_snapshot.py")
    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)
    assert payload["mesh_prefix"] == "solid W1"
    assert payload["cad_prefix"] == ["cad", "step"]
