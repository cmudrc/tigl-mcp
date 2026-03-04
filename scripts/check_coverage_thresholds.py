"""Enforce a minimum coverage threshold from pytest-cov JSON output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_MINIMUM = 85.0


def _load_total_percent(coverage_json: Path) -> float:
    """Read the total percentage from a coverage JSON file."""
    payload = json.loads(coverage_json.read_text(encoding="utf-8"))
    return float(payload["totals"]["percent_covered"])


def main() -> int:
    """Validate the coverage percentage against the configured minimum."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-json", required=True)
    parser.add_argument("--minimum", type=float, default=DEFAULT_MINIMUM)
    args = parser.parse_args()

    coverage_json = Path(args.coverage_json)
    percent = _load_total_percent(coverage_json)
    if percent < args.minimum:
        raise SystemExit(
            f"Coverage {percent:.2f}% is below the required minimum "
            f"{args.minimum:.2f}%."
        )
    print(
        f"Coverage {percent:.2f}% meets the minimum {args.minimum:.2f}%."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
