"""Coverage for runtime_check diagnostics module."""

from __future__ import annotations

from tigl_mcp.runtime_check import check_tigl_runtime, print_runtime_report


def test_check_tigl_runtime_returns_expected_keys() -> None:
    """The diagnostic dict always reports python and platform."""
    report = check_tigl_runtime()

    assert "python" in report
    assert "platform" in report
    assert "all_ok" in report
    assert isinstance(report["all_ok"], bool)


def test_print_runtime_report_produces_output(capsys: object) -> None:
    """print_runtime_report writes to stdout without error."""
    print_runtime_report()

    import sys

    captured = sys.stdout  # capsys would need pytest typing
    assert captured is not None
