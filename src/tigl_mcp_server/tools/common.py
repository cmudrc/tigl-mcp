"""Shared helpers for MCP tools."""

from __future__ import annotations

from tigl_mcp_server.cpacs import (
    BoundingBox,
    CPACSConfiguration,
    TiglConfiguration,
    TixiDocument,
)
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager


def require_session(
    session_manager: SessionManager, session_id: str
) -> tuple[TixiDocument, TiglConfiguration, CPACSConfiguration]:
    """Retrieve a session or raise an MCP-friendly error."""
    try:
        return session_manager.get(session_id)
    except MCPError:
        raise
    except Exception as exc:  # pragma: no cover - defensive path
        raise_mcp_error("SessionError", "Failed to access session", str(exc))


def format_bounding_box(box: BoundingBox | dict[str, float]) -> dict[str, float]:
    """Normalize bounding box objects to dictionaries."""
    if hasattr(box, "xmin"):
        typed_box = box  # type: ignore[assignment]
        return {
            "xmin": typed_box.xmin,
            "xmax": typed_box.xmax,
            "ymin": typed_box.ymin,
            "ymax": typed_box.ymax,
            "zmin": typed_box.zmin,
            "zmax": typed_box.zmax,
        }
    return {
        "xmin": float(box["xmin"]),
        "xmax": float(box["xmax"]),
        "ymin": float(box["ymin"]),
        "ymax": float(box["ymax"]),
        "zmin": float(box["zmin"]),
        "zmax": float(box["zmax"]),
    }
