"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

# Note on the span/area attributes below: real CPACS does not store span or
# area as attributes on <wing>; they live in the section and positioning
# geometry. They are kept here only because the high-level-parameter tools read
# numeric attributes generically, and those tests need something to read. Do
# not treat this fixture as a model of real CPACS layout. The sections and
# segments elements below *are* realistic, and are what the component counters
# parse.
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
                    <wing uID="W1" name="MainWing"
                         span="30.0" area="80.0" symmetry="x-z">
                        <sections>
                            <section uID="W1_sec1" />
                            <section uID="W1_sec2" />
                            <section uID="W1_sec3" />
                        </sections>
                        <segments>
                            <segment uID="W1_seg1" />
                            <segment uID="W1_seg2" />
                        </segments>
                        <componentSegments>
                            <componentSegment uID="W1_cseg1" />
                        </componentSegments>
                    </wing>
                </wings>
                <fuselages>
                    <fuselage uID="F1" name="Fuse" length="25.0">
                        <sections>
                            <section uID="F1_sec1" />
                            <section uID="F1_sec2" />
                        </sections>
                        <segments>
                            <segment uID="F1_seg1" />
                        </segments>
                    </fuselage>
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
