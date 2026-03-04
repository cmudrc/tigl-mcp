"""Custom error types for MCP tooling."""

from __future__ import annotations

from typing import NoReturn, TypedDict


class MCPErrorPayload(TypedDict):
    """Structured JSON payload for MCP errors."""

    error: dict[str, object | None]


class MCPError(Exception):
    """Structured MCP error containing a JSON-friendly payload."""

    def __init__(
        self, error_type: str, message: str, details: object | None = None
    ) -> None:
        """Create a structured MCP error payload."""
        super().__init__(message)
        self.error: MCPErrorPayload = {
            "error": {
                "type": error_type,
                "message": message,
                "details": details,
            }
        }

    def to_dict(self) -> MCPErrorPayload:
        """Return the structured error payload."""
        return self.error


def raise_mcp_error(
    error_type: str, message: str, details: object | None = None
) -> NoReturn:
    """Raise an :class:`MCPError` with a structured payload."""
    raise MCPError(error_type=error_type, message=message, details=details)
