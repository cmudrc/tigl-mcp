"""Test-friendly stand-in for the TiGL 3 API."""

from __future__ import annotations

from tigl_mcp_server.cpacs import TiglConfiguration, TixiDocument, parse_cpacs


def tiglOpenCPACSConfiguration(
    tixi_handle: TixiDocument, _config_uid: str | None
) -> TiglConfiguration:  # noqa: N802
    """Create a lightweight configuration using the provided TiXI handle."""
    configuration = parse_cpacs(tixi_handle.xml_content)
    return TiglConfiguration(cpacs_configuration=configuration)


def tiglCloseCPACSConfiguration(configuration: TiglConfiguration) -> None:  # noqa: N802
    """Close the provided TiGL configuration handle."""
    configuration.close()
