"""Tools for opening and closing CPACS sessions."""

from __future__ import annotations

import pathlib
from typing import Any, Literal

from tigl_mcp_server import cpacs_stubs
from tigl_mcp_server.cpacs import parse_cpacs
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tooling import ToolDefinition, ToolParameters

try:  # real bindings (preferred)
    from tixi3 import tixi3wrapper
    from tigl3 import tigl3wrapper
except Exception:  # pragma: no cover
    tixi3wrapper = None  # type: ignore[assignment]
    tigl3wrapper = None  # type: ignore[assignment]


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

    def _open_real_cpacs_from_xml(xml_content: str):

        tixi = tixi3wrapper.Tixi3()

        # tixi3 supports openString in your container (you already verified this)
        if hasattr(tixi, "openString"):
            tixi.openString(xml_content)
        elif hasattr(tixi, "openDocumentFromString"):
            tixi.openDocumentFromString(xml_content)
        else:
            raise RuntimeError("No supported TIXI open-from-string API found")

        tigl = tigl3wrapper.Tigl3()
        # your test showed this works:
        tigl.open(tixi, "")

        return tixi, tigl

    
    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = OpenCpacsParams.model_validate(raw_params)
            if params.source_type == "path":
                path = pathlib.Path(params.source)
                if not path.exists():
                    raise_mcp_error("InvalidInput", f"File not found: {path}")
                xml_content = path.read_text(encoding="utf-8")
                file_name = str(path)
            else:
                xml_content = params.source
                file_name = None

            if tixi3wrapper is None or tigl3wrapper is None:
                raise_mcp_error(
                    "OpenError",
                    "Real tigl3/tixi3 bindings not available.",
                    "Run inside the Docker image that contains tigl3/tixi3.",
                )

            # Open CPACS in-memory (avoids host/container path issues)
            tixi_handle: Any = tixi3wrapper.Tixi3()
            if hasattr(tixi_handle, "openString"):
                tixi_handle.openString(xml_content)
            elif hasattr(tixi_handle, "openDocumentFromString"):
                tixi_handle.openDocumentFromString(xml_content)
            else:
                raise_mcp_error("OpenError", "No supported TIXI open-from-string API found.")

            tigl_handle: Any = tigl3wrapper.Tigl3()
            tigl_handle.open(tixi_handle, "")

            # Lightweight parse for component listing
            cpacs_config = parse_cpacs(xml_content)


            session_id = session_manager.create_session(tixi_handle, tigl_handle, cpacs_config)
            summary = {
                "num_wings": len(cpacs_config.wings),
                "num_fuselages": len(cpacs_config.fuselages),
                "num_rotors": len(cpacs_config.rotors),
                "num_engines": len(cpacs_config.engines),
            }

            return {
                "session_id": session_id,
                "cpacs_metadata": cpacs_stubs.extract_metadata(xml_content, file_name),
                "configuration_summary": summary,
            }
        except MCPError as error:
            raise error
        except Exception as exc:  # pragma: no cover - defensive path
            raise_mcp_error("OpenError", "Failed to open CPACS", str(exc))

    return ToolDefinition(
        name="open_cpacs",
        description="Open a CPACS session from a file path or an XML string.",
        parameters_model=OpenCpacsParams,
        handler=handler,
        output_schema={},
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
