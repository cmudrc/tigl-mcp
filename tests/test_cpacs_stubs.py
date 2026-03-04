"""Contract tests for deterministic CPACS/TiGL stub behavior."""

from __future__ import annotations

from tigl_mcp_server.cpacs import BoundingBox, extract_metadata, parse_cpacs


def test_parse_cpacs_extracts_stub_components(sample_cpacs_xml: str) -> None:
    """The parser extracts lightweight component records from CPACS XML."""
    config = parse_cpacs(sample_cpacs_xml)

    assert len(config.wings) == 1
    assert len(config.fuselages) == 1
    assert len(config.rotors) == 0
    assert len(config.engines) == 0

    wing = config.wings[0]
    fuselage = config.fuselages[0]

    assert wing.uid == "W1"
    assert wing.parameters["span"] == 30.0
    assert wing.parameters["area"] == 80.0
    assert wing.symmetry == "x-z"
    assert fuselage.uid == "F1"
    assert fuselage.parameters["length"] == 25.0


def test_extract_metadata_reads_header_fields(sample_cpacs_xml: str) -> None:
    """Metadata extraction uses CPACS header content plus the optional file name."""
    metadata = extract_metadata(sample_cpacs_xml, "fixture.cpacs.xml")

    assert metadata == {
        "file_name": "fixture.cpacs.xml",
        "creator": "Unit Test",
        "description": "Sample CPACS content",
    }


def test_bounding_box_generation_is_deterministic() -> None:
    """Stub bounding boxes are deterministic functions of component index."""
    first = BoundingBox.from_index(1)
    second = BoundingBox.from_index(2)
    combined = BoundingBox.combine([first, second])

    assert first.xmin == 1.0
    assert first.xmax == 2.0
    assert second.ymin == -2.0
    assert combined.xmax == 3.0
    assert combined.ymin == -2.0
