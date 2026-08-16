"""Utility models and parsing helpers for CPACS content.

This module reads facts that are stated directly in the CPACS XML: component
UIDs, names, symmetry flags, and section/segment counts. Those are real values
taken from the file.

It deliberately computes **no** geometry. Deriving a span, an area, a bounding
box, or a surface point from CPACS requires evaluating the profile geometry
through the positioning and transformation chain, which is what TiGL exists to
do. Anything here that needs geometry reports it as unavailable rather than
approximating it, so a caller can never mistake an estimate for a TiGL result.
See ``tigl_mcp.cpacs_adapter.export_step`` for the real-TiGL path.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from xml.etree import ElementTree as ET


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float

    @classmethod
    def combine(cls, boxes: Iterable[BoundingBox | None]) -> BoundingBox | None:
        """Combine bounding boxes into a single envelope.

        Returns ``None`` when no real box is available, rather than an empty
        box at the origin, which would read as a genuine measurement.
        """
        real = [box for box in boxes if box is not None]
        if not real:
            return None

        boxes = real
        return cls(
            xmin=min(box.xmin for box in boxes),
            xmax=max(box.xmax for box in boxes),
            ymin=min(box.ymin for box in boxes),
            ymax=max(box.ymax for box in boxes),
            zmin=min(box.zmin for box in boxes),
            zmax=max(box.zmax for box in boxes),
        )


@dataclass
class ComponentDefinition:
    """Description of a CPACS component.

    Every field here is read from the CPACS file. ``bounding_box`` is ``None``
    unless a real geometry kernel supplied one; it is never estimated.
    """

    uid: str
    name: str
    index: int
    type_name: str
    symmetry: str | None
    parameters: dict[str, float]
    section_count: int = 0
    segment_count: int = 0
    component_segment_count: int = 0
    bounding_box: BoundingBox | None = None


@dataclass
class CPACSConfiguration:
    """Parsed CPACS configuration used by the MCP tools."""

    wings: list[ComponentDefinition]
    fuselages: list[ComponentDefinition]
    rotors: list[ComponentDefinition]
    engines: list[ComponentDefinition]

    def all_components(self) -> list[ComponentDefinition]:
        """Return all components in a single list."""
        return [*self.wings, *self.fuselages, *self.rotors, *self.engines]

    def bounding_box(self) -> BoundingBox | None:
        """Envelope covering all components, or ``None`` if none is known."""
        return BoundingBox.combine(
            component.bounding_box for component in self.all_components()
        )

    def find_component(self, uid: str) -> ComponentDefinition | None:
        """Locate a component by UID (exact match first, then case-insensitive)."""
        for component in self.all_components():
            if component.uid == uid:
                return component
        uid_lower = uid.lower()
        for component in self.all_components():
            if component.uid.lower() == uid_lower:
                return component
        return None


@dataclass
class TixiDocument:
    """Lightweight TiXI document stub."""

    xml_content: str
    file_name: str | None = None
    closed: bool = False

    def close(self) -> None:
        """Mark the document as closed."""
        self.closed = True


@dataclass
class TiglConfiguration:
    """Lightweight TiGL configuration stub."""

    cpacs_configuration: CPACSConfiguration
    closed: bool = False

    def close(self) -> None:
        """Mark the configuration as closed."""
        self.closed = True

    def getWingCount(self) -> int:  # noqa: N802 - mimic TiGL naming
        """Return the number of wings in the configuration."""
        return len(self.cpacs_configuration.wings)

    def getFuselageCount(self) -> int:  # noqa: N802 - mimic TiGL naming
        """Return the number of fuselages in the configuration."""
        return len(self.cpacs_configuration.fuselages)

    def getRotorCount(self) -> int:  # noqa: N802 - mimic TiGL naming
        """Return the number of rotors in the configuration."""
        return len(self.cpacs_configuration.rotors)

    def getEngineCount(self) -> int:  # noqa: N802 - mimic TiGL naming
        """Return the number of engines in the configuration."""
        return len(self.cpacs_configuration.engines)


def _count_children(element: ET.Element, container: str, child: str) -> int:
    """Count ``container/child`` entries directly under a component element."""
    holder = element.find(container)
    if holder is None:
        return 0
    return len(holder.findall(child))


def _find_component_elements(
    root: ET.Element, container: str, tag: str
) -> list[ET.Element]:
    """Locate aircraft components, excluding tool-specific extension blocks.

    A bare ``.//wing`` search is wrong: CPACS files carry vendor blocks under
    ``toolspecific/`` that use the same element names. The D150 has three
    wings and one fuselage, but ``.//wing`` matches five and ``.//fuselage``
    two, because ``toolspecific/paramamSBot`` and ``toolspecific/boxBeam``
    each contain their own ``<wing>``. Requiring the plural container, and
    preferring the aircraft model subtree, keeps the count to real components.
    """
    model = root.find(".//vehicles/aircraft/model")
    if model is not None:
        holder = model.find(container)
        if holder is not None:
            return holder.findall(tag)
        return []
    # Fragment or non-standard root: still require the plural container, which
    # is what excludes the toolspecific blocks.
    return root.findall(f".//{container}/{tag}")


def _parse_components(
    root: ET.Element, container: str, tag: str
) -> list[ComponentDefinition]:
    """Parse CPACS components of a given tag."""
    components: list[ComponentDefinition] = []
    for index, element in enumerate(
        _find_component_elements(root, container, tag), start=1
    ):
        # CPACS commonly uses "uID" while fixtures may use lowercase "uid".
        uid = element.get("uID") or element.get("uid") or f"{tag}_{index}"
        name = element.get("name") or uid
        symmetry = element.get("symmetry")
        parameters: dict[str, float] = {}
        for attr, raw in element.attrib.items():
            if attr in {"uid", "uID", "name", "symmetry"}:
                continue
            try:
                parameters[attr] = float(raw)
            except ValueError:
                continue
        components.append(
            ComponentDefinition(
                uid=uid,
                name=name,
                index=index,
                type_name=tag.capitalize(),
                symmetry=symmetry,
                parameters=parameters,
                section_count=_count_children(element, "sections", "section"),
                segment_count=_count_children(element, "segments", "segment"),
                component_segment_count=_count_children(
                    element, "componentSegments", "componentSegment"
                ),
                # No bounding box: computing one needs the profile geometry
                # evaluated through the transformation chain, i.e. TiGL.
                bounding_box=None,
            )
        )
    return components


def parse_cpacs(xml_content: str) -> CPACSConfiguration:
    """Parse CPACS XML content into a configuration representation."""
    root = ET.fromstring(xml_content)
    wings = _parse_components(root, "wings", "wing")
    fuselages = _parse_components(root, "fuselages", "fuselage")
    rotors = _parse_components(root, "rotors", "rotor")
    engines = _parse_components(root, "engines", "engine")
    return CPACSConfiguration(
        wings=wings, fuselages=fuselages, rotors=rotors, engines=engines
    )


def extract_metadata(xml_content: str, file_name: str | None) -> dict[str, str | None]:
    """Extract common header metadata from CPACS content."""
    root = ET.fromstring(xml_content)
    creator_node = root.find(".//header/creator")
    description_node = root.find(".//header/description")
    return {
        "file_name": file_name,
        "creator": creator_node.text if creator_node is not None else None,
        "description": description_node.text if description_node is not None else None,
    }


def build_handles(
    xml_content: str, file_name: str | None
) -> tuple[TixiDocument, TiglConfiguration, CPACSConfiguration, dict[str, str | None]]:
    """Create TiXI/TiGL stand-ins from XML content."""
    tixi_document = TixiDocument(xml_content=xml_content, file_name=file_name)
    configuration = parse_cpacs(xml_content)
    tigl_configuration = TiglConfiguration(cpacs_configuration=configuration)
    metadata = extract_metadata(xml_content, file_name)
    return tixi_document, tigl_configuration, configuration, metadata
