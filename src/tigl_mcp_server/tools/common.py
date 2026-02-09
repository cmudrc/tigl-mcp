"""Shared helpers for MCP tools."""

from __future__ import annotations

from typing import TypedDict

from tigl_mcp_server.cpacs import (
    BoundingBox,
    CPACSConfiguration,
    TiglConfiguration,
    TixiDocument,
)
from tigl_mcp_server.errors import MCPError, raise_mcp_error
from tigl_mcp_server.session_manager import SessionManager


class BoundingBoxDict(TypedDict):
    """Dictionary representation of a bounding box."""

    xmin: float
    xmax: float
    ymin: float
    ymax: float
    zmin: float
    zmax: float


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


def format_bounding_box(box: BoundingBox | BoundingBoxDict) -> BoundingBoxDict:
    """Normalize bounding box objects to dictionaries."""
    if isinstance(box, BoundingBox):
        return {
            "xmin": box.xmin,
            "xmax": box.xmax,
            "ymin": box.ymin,
            "ymax": box.ymax,
            "zmin": box.zmin,
            "zmax": box.zmax,
        }
    return {
        "xmin": float(box["xmin"]),
        "xmax": float(box["xmax"]),
        "ymin": float(box["ymin"]),
        "ymax": float(box["ymax"]),
        "zmin": float(box["zmin"]),
        "zmax": float(box["zmax"]),
    }
