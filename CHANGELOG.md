# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2024-11-29
### Added
- Initial MCP scaffold with in-memory server, dummy tool, and CLI.
- Testing infrastructure with pytest and coverage configuration.
- Project metadata and development tooling configuration via `pyproject.toml`.

## [0.2.0] - 2025-03-01
### Added
- FastMCP integration for the TiGL toolset with stdio and HTTP transports.
- Adapter layer that registers existing tools with FastMCP while preserving session management.
- End-to-end FastMCP protocol tests that exercise tool discovery and error propagation.
