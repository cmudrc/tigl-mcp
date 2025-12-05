"""Tools for opening and closing CPACS sessions."""

from __future__ import annotations

import pathlib
from typing import Literal

from tigl_mcp_server import cpacs_stubs
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters


class OpenCpacsParams(ToolParameters):
    """Parameters for the open_cpacs tool."""

    source_type: Literal["path", "xml_string"]
    source: str


class CloseCpacsParams(ToolParameters):
    """Parameters for the close_cpacs tool."""

    session_id: str


def _read_source(params: OpenCpacsParams) -> tuple[str, str | None]:
    if params.source_type == "path":
        path = pathlib.Path(params.source)
        if not path.exists():
            raise_mcp_error("InvalidInput", f"File not found: {path}")
        return path.read_text(encoding="utf-8"), str(path)
    return params.source, None


def open_cpacs_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the open_cpacs tool definition."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = OpenCpacsParams.model_validate(raw_params)
            xml_content, file_name = _read_source(params)
            tixi_handle = cpacs_stubs.tixiOpenDocumentFromString(xml_content)
            tigl_handle = cpacs_stubs.tiglOpenCPACSConfiguration(tixi_handle, None)
            session_id = session_manager.create_session(
                tixi_handle, tigl_handle, tigl_handle.cpacs_configuration
            )
            summary = {
                "num_wings": tigl_handle.getWingCount(),
                "num_fuselages": tigl_handle.getFuselageCount(),
                "num_rotors": tigl_handle.getRotorCount(),
                "num_engines": tigl_handle.getEngineCount(),
            }
            return {
                "session_id": session_id,
                "cpacs_metadata": cpacs_stubs.extract_metadata(
                    xml_content, file_name
                ),
                "configuration_summary": summary,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("OpenError", "Failed to open CPACS", str(exc))

    return ToolDefinition(
        name="open_cpacs",
        description="Open a CPACS document and create a TiGL configuration.",
        parameters_model=OpenCpacsParams,
        handler=handler,
        output_schema={
            "session_id": "string",
            "cpacs_metadata": "object",
            "configuration_summary": "object",
        },
    )


def close_cpacs_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the close_cpacs tool definition."""

    def handler(raw_params: dict[str, object]) -> dict[str, bool]:
        try:
            params = CloseCpacsParams.model_validate(raw_params)
            session_manager.close(params.session_id)
            return {"success": True}
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("CloseError", "Failed to close CPACS", str(exc))

    return ToolDefinition(
        name="close_cpacs",
        description="Close a CPACS session and free resources.",
        parameters_model=CloseCpacsParams,
        handler=handler,
        output_schema={"success": "boolean"},
    )
