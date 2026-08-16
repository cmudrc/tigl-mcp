"""Contract tests for CPACS parsing.

These assert that parsing reports only what the file states, and that
geometry it cannot compute is reported as absent rather than estimated.
"""

from __future__ import annotations

from tigl_mcp.cpacs import BoundingBox, extract_metadata, parse_cpacs


def test_parse_cpacs_extracts_components(sample_cpacs_xml: str) -> None:
    """The parser extracts component records from CPACS XML."""
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


def test_parse_cpacs_accepts_camel_case_uid_attribute() -> None:
    """CPACS camelCase ``uID`` attributes are treated as primary identifiers."""
    xml = """
    <cpacs>
      <vehicles>
        <aircraft>
          <model>
            <wings>
              <wing uID="WingCamelCase" span="1.0" />
            </wings>
          </model>
        </aircraft>
      </vehicles>
    </cpacs>
    """.strip()
    config = parse_cpacs(xml)

    assert config.wings[0].uid == "WingCamelCase"


def test_find_component_supports_case_insensitive_lookup(
    sample_cpacs_xml: str,
) -> None:
    """Component lookup falls back to case-insensitive matching."""
    config = parse_cpacs(sample_cpacs_xml)
    component = config.find_component("w1")

    assert component is not None
    assert component.uid == "W1"


def test_extract_metadata_reads_header_fields(sample_cpacs_xml: str) -> None:
    """Metadata extraction uses CPACS header content plus the optional file name."""
    metadata = extract_metadata(sample_cpacs_xml, "fixture.cpacs.xml")

    assert metadata == {
        "file_name": "fixture.cpacs.xml",
        "creator": "Unit Test",
        "description": "Sample CPACS content",
    }


def test_parsed_components_have_no_bounding_box(sample_cpacs_xml: str) -> None:
    """Parsing must not invent geometry.

    CPACS carries no bounding boxes, so a parsed component reports ``None``
    rather than an estimate. Regression guard for the removed
    ``BoundingBox.from_index``, which returned a box derived from the
    component's array position and wrote it into the shared CPACS document.
    """
    config = parse_cpacs(sample_cpacs_xml)

    for component in config.all_components():
        assert component.bounding_box is None
    assert config.bounding_box() is None


def test_combine_ignores_missing_boxes_and_reports_none_when_empty() -> None:
    """Combining real boxes works; combining nothing yields None, not zeros."""
    first = BoundingBox(1.0, 2.0, -1.0, 1.0, -0.5, 0.5)
    second = BoundingBox(0.0, 5.0, -3.0, 3.0, -1.0, 2.0)

    combined = BoundingBox.combine([first, None, second])
    assert combined is not None
    assert combined.xmin == 0.0
    assert combined.xmax == 5.0
    assert combined.ymin == -3.0
    assert combined.zmax == 2.0

    # An empty envelope must not read as a real measurement at the origin.
    assert BoundingBox.combine([]) is None
    assert BoundingBox.combine([None, None]) is None


def test_toolspecific_blocks_are_not_counted_as_components() -> None:
    """Vendor blocks reusing component element names must not inflate counts.

    Real CPACS files (the D150 among them) carry ``<wing>`` and ``<fuselage>``
    elements under ``toolspecific/``. Counting those reported the D150 as
    having five wings and two fuselages instead of three and one.
    """
    xml = """
    <cpacs>
      <vehicles>
        <aircraft>
          <model>
            <wings>
              <wing uID="RealWing" />
            </wings>
            <fuselages>
              <fuselage uID="RealFuse" />
            </fuselages>
          </model>
        </aircraft>
      </vehicles>
      <toolspecific>
        <paramamSBot>
          <wing uID="NotAComponent" />
          <fuselage uID="AlsoNotAComponent" />
        </paramamSBot>
        <boxBeam>
          <wing uID="StillNotAComponent" />
        </boxBeam>
      </toolspecific>
    </cpacs>
    """.strip()

    config = parse_cpacs(xml)

    assert [wing.uid for wing in config.wings] == ["RealWing"]
    assert [f.uid for f in config.fuselages] == ["RealFuse"]


def test_section_and_segment_counts_come_from_the_file(sample_cpacs_xml: str) -> None:
    """Counts are parsed from CPACS, not defaulted to zero."""
    config = parse_cpacs(sample_cpacs_xml)
    wing = config.wings[0]
    fuselage = config.fuselages[0]

    assert wing.section_count == 3
    assert wing.segment_count == 2
    assert wing.component_segment_count == 1
    assert fuselage.section_count == 2
    assert fuselage.segment_count == 1
