# Examples

These examples exercise the current deterministic, stub-backed implementation.
They are designed to run from the repository root with `PYTHONPATH=src`.

- `client/tool_discovery.py`: list the registered MCP tools via the in-process FastMCP app.
- `cpacs/session_lifecycle.py`: open CPACS XML, inspect the summary, and close the session.
- `cpacs/export_snapshot.py`: export stubbed mesh and CAD payloads from a sample session.
- `server/http_launch_config.py`: show the non-blocking HTTP transport configuration shape.
