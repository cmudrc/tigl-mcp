"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_CPACS_XML = """
<cpacs>
    <header>
        <creator>Unit Test</creator>
        <description>Sample CPACS content</description>
    </header>
    <vehicles>
        <aircraft>
            <model>
                <wings>
                    <wing uid="W1" name="MainWing"
                         span="30.0" area="80.0" symmetry="x-z" />
                </wings>
                <fuselages>
                    <fuselage uid="F1" name="Fuse" length="25.0" />
                </fuselages>
            </model>
        </aircraft>
    </vehicles>
</cpacs>
""".strip()


@pytest.fixture()
def sample_cpacs_xml() -> str:
    """Provide a small CPACS-like XML document for testing."""
    return SAMPLE_CPACS_XML


@pytest.fixture()
def sample_cpacs_path(tmp_path: Path, sample_cpacs_xml: str) -> Path:
    """Persist a sample CPACS file for path-based tool and example testing."""
    cpacs_path = tmp_path / "sample.cpacs.xml"
    cpacs_path.write_text(sample_cpacs_xml, encoding="utf-8")
    return cpacs_path
