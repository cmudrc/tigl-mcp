"""Every write is recorded in the CPACS ``header/updates`` provenance list."""

from __future__ import annotations

import importlib.metadata
import re
from xml.etree import ElementTree as ET

from tigl_mcp.cpacs_adapter import write_to_cpacs

PACKAGE = "tigl-mcp"
RESULTS = {"wing_count": 1, "fuselage_count": 1, "components": []}
RESULTS_NODE = ".//vehicles/aircraft/model/analysisResults/tigl"

# A CPACS 3.x header with its children in schema order and no updates list yet.
HEADER_WITHOUT_UPDATES = (
    "<cpacs><header><name>Sample</name><description>Unit test</description>"
    "<creator>Unit Test</creator><timestamp>2020-01-01T00:00:00</timestamp>"
    "<version>0.1</version><cpacsVersion>3.2</cpacsVersion></header>"
    "<vehicles><aircraft><model/></aircraft></vehicles></cpacs>"
)
# The same header already carrying one update from another tool.
HEADER_WITH_UPDATES = HEADER_WITHOUT_UPDATES.replace(
    "</cpacsVersion></header>",
    "</cpacsVersion><updates><update>"
    "<modification>Converted to CPACS 3.2</modification>"
    "<creator>cpacs2to3</creator><timestamp>2021-05-01T10:00:00</timestamp>"
    "<version>0.1</version><cpacsVersion>3.2</cpacsVersion>"
    "</update></updates></header>",
)
HEADER_WITH_VERSION_ONLY = (
    "<cpacs><header><name>Sample</name><version>0.1</version>"
    "<creator>Unit Test</creator></header>"
    "<vehicles><aircraft><model/></aircraft></vehicles></cpacs>"
)
HEADER_WITHOUT_VERSIONS = (
    "<cpacs><header><name>Sample</name></header>"
    "<vehicles><aircraft><model/></aircraft></vehicles></cpacs>"
)
NO_HEADER = "<cpacs><vehicles><aircraft><model/></aircraft></vehicles></cpacs>"

TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _header(xml: str) -> ET.Element:
    header = ET.fromstring(xml).find("header")
    assert header is not None
    return header


def _updates(xml: str) -> list[ET.Element]:
    return ET.fromstring(xml).findall("header/updates/update")


def test_write_appends_one_update_with_the_five_children_in_order() -> None:
    out = write_to_cpacs(HEADER_WITHOUT_UPDATES, RESULTS)
    assert ET.fromstring(out).find(RESULTS_NODE) is not None
    updates = _updates(out)
    assert len(updates) == 1
    update = updates[0]
    assert [child.tag for child in update] == [
        "modification",
        "creator",
        "timestamp",
        "version",
        "cpacsVersion",
    ]
    assert update.findtext("modification", "").startswith(PACKAGE + " wrote ")
    assert TIMESTAMP.match(update.findtext("timestamp", ""))
    assert update.findtext("version") == "1"
    assert update.findtext("cpacsVersion") == "3.2"


def test_creator_is_the_package_name_and_installed_version() -> None:
    try:
        version = importlib.metadata.version(PACKAGE)
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    update = _updates(write_to_cpacs(HEADER_WITHOUT_UPDATES, RESULTS))[0]
    assert update.findtext("creator") == f"{PACKAGE} {version}"


def test_second_write_increments_the_running_version() -> None:
    once = write_to_cpacs(HEADER_WITHOUT_UPDATES, RESULTS)
    twice = write_to_cpacs(once, RESULTS)
    assert [u.findtext("version") for u in _updates(twice)] == ["1", "2"]
    # The results node is replaced, not duplicated; only the provenance grows.
    assert len(ET.fromstring(twice).findall(RESULTS_NODE)) == 1


def test_updates_written_by_other_tools_are_kept_and_counted() -> None:
    updates = _updates(write_to_cpacs(HEADER_WITH_UPDATES, RESULTS))
    assert len(updates) == 2
    assert updates[0].findtext("creator") == "cpacs2to3"
    assert updates[1].findtext("version") == "2"


def test_missing_updates_list_is_created_directly_after_cpacs_version() -> None:
    header = _header(write_to_cpacs(HEADER_WITHOUT_UPDATES, RESULTS))
    assert [child.tag for child in header] == [
        "name",
        "description",
        "creator",
        "timestamp",
        "version",
        "cpacsVersion",
        "updates",
    ]


def test_missing_updates_list_falls_back_to_after_version() -> None:
    header = _header(write_to_cpacs(HEADER_WITH_VERSION_ONLY, RESULTS))
    assert [child.tag for child in header] == ["name", "version", "updates", "creator"]
    # Without a cpacsVersion the entry copies the document version instead.
    assert header.findtext("updates/update/cpacsVersion") == "0.1"


def test_missing_updates_list_falls_back_to_end_of_header() -> None:
    header = _header(write_to_cpacs(HEADER_WITHOUT_VERSIONS, RESULTS))
    assert [child.tag for child in header] == ["name", "updates"]
    assert header.findtext("updates/update/cpacsVersion") == ""


def test_document_without_header_gets_one_as_first_child() -> None:
    root = ET.fromstring(write_to_cpacs(NO_HEADER, RESULTS))
    assert [child.tag for child in root] == ["header", "vehicles"]
    update = root.find("header/updates/update")
    assert update is not None
    assert update.findtext("version") == "1"
    assert update.findtext("cpacsVersion") == ""


def test_existing_header_children_are_untouched() -> None:
    before = _header(HEADER_WITH_UPDATES)
    after = _header(write_to_cpacs(HEADER_WITH_UPDATES, RESULTS))
    assert [child.tag for child in after] == [child.tag for child in before]
    for tag in (
        "name",
        "description",
        "creator",
        "timestamp",
        "version",
        "cpacsVersion",
    ):
        assert after.findtext(tag) == before.findtext(tag)
    earlier = before.find("updates/update")
    assert earlier is not None
    kept = after.find("updates/update")
    assert kept is not None
    assert ET.tostring(kept, encoding="unicode") == ET.tostring(
        earlier, encoding="unicode"
    )


def test_sample_fixture_header_is_extended_not_rewritten(sample_cpacs_xml: str) -> None:
    # The shared fixture header states neither version nor cpacsVersion, so the
    # updates list goes last and the entry's cpacsVersion is left empty.
    before = _header(sample_cpacs_xml)
    header = _header(write_to_cpacs(sample_cpacs_xml, RESULTS))
    assert [child.tag for child in header] == [*(c.tag for c in before), "updates"]
    assert header.findtext("creator") == before.findtext("creator")
    assert header.findtext("updates/update/cpacsVersion") == ""
