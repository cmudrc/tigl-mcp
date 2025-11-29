"""Tests for the MCP server scaffold."""

from __future__ import annotations

import json

import pytest

from tigl_mcp.server import MCPServer
from tigl_mcp.tools import register_dummy_tool


class TestMCPServer:
    """Behavioral coverage for MCPServer."""

    def test_register_and_list_tools(self) -> None:
        """Registers a tool and ensures it appears in the catalog."""
        # Arrange
        server = MCPServer()
        dummy = register_dummy_tool()

        # Act
        server.register_tool(dummy)

        # Assert
        assert server.available_tools() == ["dummy"]
        catalog = server.to_catalog()
        assert "dummy" in catalog
        assert catalog["dummy"]["description"] == dummy.description

    def test_prevents_duplicate_tool_names(self) -> None:
        """Duplicate tool registrations raise a ValueError."""
        # Arrange
        server = MCPServer()
        dummy = register_dummy_tool()
        server.register_tool(dummy)

        # Act / Assert
        with pytest.raises(ValueError):
            server.register_tool(dummy)

    def test_runs_registered_tool(self) -> None:
        """Executing a registered tool returns its payload."""
        # Arrange
        server = MCPServer()
        server.register_tool(register_dummy_tool())

        # Act
        result = server.run_tool("dummy")

        # Assert
        assert result.name == "dummy"
        assert result.payload["status"] == "ok"
        assert json.loads(result.to_json())["payload"]["message"]

    def test_running_unknown_tool_errors(self) -> None:
        """Unknown tool invocations raise a KeyError."""
        # Arrange
        server = MCPServer()

        # Act / Assert
        with pytest.raises(KeyError):
            server.run_tool("missing")

    def test_rejects_invalid_parameters(self) -> None:
        """Invalid parameters are surfaced as validation errors."""
        # Arrange
        server = MCPServer()
        dummy = register_dummy_tool()
        server.register_tool(dummy)

        # Act / Assert
        with pytest.raises(ValueError):
            server.run_tool("dummy", parameters={"unexpected": "value"})
