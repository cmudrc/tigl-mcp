"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture()
def sample_cpacs_xml() -> str:
    """Provide a small CPACS-like XML document for testing."""
    return """
    <cpacs>
        <header>
            <creator>Unit Test</creator>
            <description>Sample CPACS content</description>
        </header>
        <vehicles>
            <aircraft>
                <model>
                    <wings>
                        <wing uid=\"W1\" name=\"MainWing\"
                             span=\"30.0\" area=\"80.0\" symmetry=\"x-z\" />
                    </wings>
                    <fuselages>
                        <fuselage uid=\"F1\" name=\"Fuse\" length=\"25.0\" />
                    </fuselages>
                </model>
            </aircraft>
        </vehicles>
    </cpacs>
    """
