"""Session management for TiGL/TiXI handles."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass

from tigl_mcp_server.cpacs import CPACSConfiguration, TiglConfiguration, TixiDocument
from tigl_mcp_server.errors import MCPError, raise_mcp_error


@dataclass
class SessionData:
    """Session payload stored by :class:`SessionManager`."""

    tixi_handle: TixiDocument
    tigl_handle: TiglConfiguration
    config: CPACSConfiguration


class SessionManager:
    """In-memory manager mapping session identifiers to handles."""

    def __init__(self) -> None:
        """Initialize the session manager with empty state."""
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        tixi_handle: TixiDocument,
        tigl_handle: TiglConfiguration,
        config: CPACSConfiguration,
    ) -> str:
        """Register a new session and return its identifier."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = SessionData(
                tixi_handle=tixi_handle, tigl_handle=tigl_handle, config=config
            )
        return session_id

    def get(
        self, session_id: str
    ) -> tuple[TixiDocument, TiglConfiguration, CPACSConfiguration]:
        """Retrieve handles for a session or raise an MCP error."""
        with self._lock:
            if session_id not in self._sessions:
                raise MCPError("InvalidSession", f"Unknown session_id '{session_id}'")
            data = self._sessions[session_id]
        return data.tixi_handle, data.tigl_handle, data.config

    def close(self, session_id: str) -> None:
        """Close and remove a session."""
        with self._lock:
            data = self._sessions.get(session_id)
            if data is None:
                raise_mcp_error("InvalidSession", f"Unknown session_id '{session_id}'")
            data.tigl_handle.close()
            data.tixi_handle.close()
            del self._sessions[session_id]


session_manager = SessionManager()
