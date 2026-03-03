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

## [0.3.0] - 2026-03-03
### Added
- STEP/IGES CAD export via `export_configuration_cad` tool (full aircraft via TiGL).
- STL export by component UID using TiGL meshed geometry exporters.
- Dockerfile with TiGL, Gmsh, and SU2 (supports Apple Silicon via amd64 emulation).
- Example scripts for STEP and STL export via MCP HTTP endpoint.

### Fixed
- **UID parsing**: CPACS `uID` attribute (camelCase) is now correctly read as the
  primary component identifier. Previously only lowercase `uid` was checked,
  causing real CPACS files to fall back to synthetic IDs like `wing_1`.
- **`num_triangles`**: Now counted from actual mesh bytes instead of a hardcoded
  formula.
- Component lookup now supports case-insensitive UID matching.
- Removed duplicate `.gitignore` entries and stale `export.sse.json`.

### Changed
- Moved `D150_simple.xml` to `tests/fixtures/`.
- Moved example scripts to `examples/`.
- Added `.dockerignore` to speed up Docker builds.
- Dockerfile now fails the build if SU2 is not installed correctly.
