"""Shared tool definitions for the TiGL MCP project."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

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
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    output_schema: dict[str, Any] | None = field(default=None)

    def validate(self, parameters: dict[str, Any]) -> dict[str, Any]:
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

    def metadata(self) -> dict[str, Any]:
        """Return a discovery-friendly description of the tool."""
        metadata: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "schema": self.parameters_model.model_json_schema(),
        }
        if self.output_schema is not None:
            metadata["output_schema"] = self.output_schema
        return metadata
