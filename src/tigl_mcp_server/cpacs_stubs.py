"""TiXI/TiGL-compatible stub helpers built on the internal CPACS models."""

from __future__ import annotations

from tigl_mcp_server.cpacs import (
    TiglConfiguration,
    TixiDocument,
    parse_cpacs,
)
from tigl_mcp_server.cpacs import (
    extract_metadata as cpacs_extract_metadata,
)


def tixiOpenDocument(path: str) -> TixiDocument:  # noqa: N802 - mimic TiXI naming
    """Open a CPACS document from disk and return a TiXI-like handle."""
    with open(path, encoding="utf-8") as file:
        xml_content = file.read()
    return TixiDocument(xml_content=xml_content, file_name=path)


def tixiOpenDocumentFromString(xml_content: str) -> TixiDocument:  # noqa: N802
    """Open a CPACS document from an XML string."""
    return TixiDocument(xml_content=xml_content)


def tixiCloseDocument(handle: TixiDocument) -> None:  # noqa: N802
    """Close the provided TiXI document handle."""
    handle.close()


def tiglOpenCPACSConfiguration(
    tixi_handle: TixiDocument, _config_uid: str | None
) -> TiglConfiguration:  # noqa: N802
    """Create a lightweight configuration using the provided TiXI handle."""
    configuration = parse_cpacs(tixi_handle.xml_content)
    return TiglConfiguration(cpacs_configuration=configuration)


def tiglCloseCPACSConfiguration(configuration: TiglConfiguration) -> None:  # noqa: N802
    """Close the provided TiGL configuration handle."""
    configuration.close()


def extract_metadata(xml_content: str, file_name: str | None) -> dict[str, str | None]:
    """Expose metadata extraction to mirror TiXI helpers."""
    return cpacs_extract_metadata(xml_content, file_name)
