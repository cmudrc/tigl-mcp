"""Session management for CPACS/TIXI/TiGL handles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tigl_mcp_server.cpacs import CPACSConfiguration
from tigl_mcp_server.errors import raise_mcp_error, MCPError
import threading
import uuid




@dataclass
class SessionData:
    """Session payload stored by :class:`SessionManager`."""
    session_id: str
    tixi_handle: Any
    tigl_handle: Any
    config: CPACSConfiguration


class SessionManager:
    """In-memory manager mapping session identifiers to handles."""

    def __init__(self) -> None:
        """Initialize the session manager with empty state."""
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create_session(self, tixi_handle: Any, tigl_handle: Any, config: CPACSConfiguration) -> str:
        """Register a new session and return its identifier."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = SessionData(
                session_id=session_id,tixi_handle=tixi_handle, tigl_handle=tigl_handle, config=config,
            )
        return session_id

    def get(self, session_id: str) -> SessionData:
        with self._lock:
            data = self._sessions.get(session_id)
            if data is None:
                raise_mcp_error("InvalidSession", f"Unknown session_id '{session_id}'")
            return data

    def close(self, session_id: str) -> None:
        """Close and remove a session."""
        with self._lock:
            data = self._sessions.get(session_id)
            if data is None:
                raise_mcp_error("InvalidSession", f"Unknown session_id '{session_id}'")
            def _best_effort_close(obj: Any, method_names: list[str]) -> None:
                for name in method_names:
                    fn = getattr(obj, name, None)
                    if callable(fn):
                        try:
                            fn()
                        except Exception:
                            pass
                        break

            _best_effort_close(data.tigl_handle, ["close", "closeConfiguration", "close_configuration"])
            _best_effort_close(data.tixi_handle, ["closeDocument", "close_document", "close"])
            del self._sessions[session_id]


session_manager = SessionManager()
