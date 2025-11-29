"""Custom error types for MCP tooling."""

from __future__ import annotations


class MCPError(Exception):
    """Structured MCP error containing a JSON-friendly payload."""

    def __init__(
        self, error_type: str, message: str, details: object | None = None
    ) -> None:
        """Create a structured MCP error payload."""
        super().__init__(message)
        self.error = {
            "error": {"type": error_type, "message": message, "details": details}
        }

    def to_dict(self) -> dict[str, object]:
        """Return the structured error payload."""
        return self.error


def raise_mcp_error(
    error_type: str, message: str, details: object | None = None
) -> None:
    """Raise an :class:`MCPError` with a structured payload."""
    raise MCPError(error_type=error_type, message=message, details=details)
