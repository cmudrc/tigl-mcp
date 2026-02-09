"""Utility models and parsing helpers for CPACS content.

This module offers lightweight stand-ins for TiXI/TiGL objects. The goal is to
provide predictable behavior in test environments while preserving the shape of
the real APIs. Geometry calculations are intentionally simplified; the focus is
on producing deterministic, well-structured JSON for the MCP tools.
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
    def from_index(cls, index: int) -> BoundingBox:
        """Create a simple bounding box derived from an index."""
        base = float(index)
        return cls(
            xmin=base,
            xmax=base + 1.0,
            ymin=-base,
            ymax=base + 0.5,
            zmin=-0.25 * (base + 1.0),
            zmax=0.25 * (base + 1.0),
        )

    @classmethod
    def combine(cls, boxes: Iterable[BoundingBox]) -> BoundingBox:
        """Combine multiple bounding boxes into a single envelope."""
        boxes = list(boxes)
        if not boxes:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

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
    """Description of a CPACS component."""

    uid: str
    name: str
    index: int
    type_name: str
    symmetry: str | None
    parameters: dict[str, object]
    bounding_box: BoundingBox


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

    def bounding_box(self) -> BoundingBox:
        """Envelope covering all components."""
        return BoundingBox.combine(
            component.bounding_box for component in self.all_components()
        )

    def find_component(self, uid: str) -> ComponentDefinition | None:
        """Locate a component by UID."""
        for component in self.all_components():
            if component.uid == uid:
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


def _parse_components(root: ET.Element, tag: str) -> list[ComponentDefinition]:
    components: list[ComponentDefinition] = []
    for index, element in enumerate(root.findall(f".//{tag}"), start=1):
        uid = element.get("uid") or f"{tag}_{index}" 
        name = element.get("name") or uid
        symmetry = element.get("symmetry")

        tigl_uid = element.get("uID")

        parameters: dict[str, object] = {}
        if tigl_uid:
            parameters["tigl_uid"] = tigl_uid

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
                bounding_box=BoundingBox.from_index(index),
            )
        )
    return components


def parse_cpacs(xml_content: str) -> CPACSConfiguration:
    """Parse CPACS XML content into a configuration representation."""
    root = ET.fromstring(xml_content)
    wings = _parse_components(root, "wing")
    fuselages = _parse_components(root, "fuselage")
    rotors = _parse_components(root, "rotor")
    engines = _parse_components(root, "engine")
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
