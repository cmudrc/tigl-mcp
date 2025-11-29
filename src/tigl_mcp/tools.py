"""Tool definitions for the TiGL MCP scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from pydantic import BaseModel, ConfigDict, ValidationError


class ToolParameters(BaseModel):
    """Base parameters schema for MCP tools."""

    model_config = ConfigDict(extra="forbid")


@dataclass
class ToolDefinition:
    """Description of a tool that can be registered with the server.

    Attributes:
        name: Unique name of the tool.
        description: Human-readable description of the tool purpose.
        parameters_model: Pydantic model used to validate input parameters.
        handler: Callable that executes the tool logic.
    """

    name: str
    description: str
    parameters_model: type[ToolParameters]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]

    def validate(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and coerce incoming tool parameters.

        Args:
            parameters: Input parameters provided for the tool.

        Raises:
            ValueError: If parameter validation fails.

        Returns:
            Validated parameter dictionary.
        """

        try:
            model = self.parameters_model(**parameters)
        except ValidationError as error:
            raise ValueError(f"Invalid parameters for tool '{self.name}'") from error
        return model.model_dump()

    def metadata(self) -> Dict[str, Any]:
        """Return a discovery-friendly description of the tool."""

        return {
            "name": self.name,
            "description": self.description,
            "schema": self.parameters_model.model_json_schema(),
        }


def register_dummy_tool() -> ToolDefinition:
    """Create a placeholder tool for early testing.

    Returns:
        ToolDefinition wired to the dummy handler.
    """

    class DummyParameters(ToolParameters):
        """No-op parameter schema for the dummy tool."""

    def handler(_: Dict[str, Any]) -> Dict[str, Any]:
        """Return a static response for smoke testing."""

        return {
            "status": "ok",
            "message": "Dummy tool executed successfully",
        }

    return ToolDefinition(
        name="dummy",
        description="Placeholder tool used while building out MCP plumbing.",
        parameters_model=DummyParameters,
        handler=handler,
    )
