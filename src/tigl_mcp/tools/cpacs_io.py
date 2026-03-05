"""Tools for opening and closing CPACS sessions."""

from __future__ import annotations

import pathlib
from importlib import import_module
from typing import Any, Literal, cast

from tigl_mcp import cpacs_stubs
from tigl_mcp.cpacs import build_handles, parse_cpacs
from tigl_mcp.errors import MCPError, raise_mcp_error
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition, ToolParameters


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


def _load_real_bindings() -> tuple[object | None, object | None]:
    """Load TiXI/TiGL wrappers when optional native dependencies are present."""
    try:
        tigl_wrapper = import_module("tigl3.tigl3wrapper")
        tixi_wrapper = import_module("tixi3.tixi3wrapper")
        return tixi_wrapper, tigl_wrapper
    except Exception:  # pragma: no cover - optional runtime dependency
        return None, None


def open_cpacs_tool(session_manager: SessionManager) -> ToolDefinition:
    """Create the open_cpacs tool definition."""

    def handler(raw_params: dict[str, object]) -> dict[str, object]:
        try:
            params = OpenCpacsParams.model_validate(raw_params)
            xml_content, file_name = _read_source(params)
            cpacs_config = parse_cpacs(xml_content)
            tixi3wrapper, tigl3wrapper = _load_real_bindings()

            if (
                tixi3wrapper is not None and tigl3wrapper is not None
            ):  # pragma: no cover
                tixi_module = cast(Any, tixi3wrapper)
                tigl_module = cast(Any, tigl3wrapper)

                tixi_handle: Any = tixi_module.Tixi3()
                if hasattr(tixi_handle, "openString"):
                    tixi_handle.openString(xml_content)
                elif hasattr(tixi_handle, "openDocumentFromString"):
                    tixi_handle.openDocumentFromString(xml_content)
                else:
                    raise_mcp_error(
                        "OpenError",
                        "No supported TIXI open-from-string API found.",
                    )

                tigl_handle: Any = tigl_module.Tigl3()
                tigl_handle.open(tixi_handle, "")
            else:
                tixi_handle, tigl_handle, _, _ = build_handles(xml_content, file_name)

            session_id = session_manager.create_session(
                tixi_handle, tigl_handle, cpacs_config
            )
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
