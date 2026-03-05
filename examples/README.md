# Examples

Deterministic examples exercise the current stub-backed implementation and are
designed to run from the repository root with `PYTHONPATH=src`.

- `client/tool_discovery.py`: list the registered MCP tools via the in-process FastMCP app.
- `cpacs/session_lifecycle.py`: open CPACS XML, inspect the summary, and close the session.
- `cpacs/export_snapshot.py`: export stubbed mesh and CAD payloads from a sample session.
- `server/http_launch_config.py`: show the non-blocking HTTP transport configuration shape.

Integration/network examples call a running MCP HTTP endpoint and are not part of
the deterministic smoke suite:

- `http/export_stl_http.py`: open CPACS from XML and export component STL via HTTP.
- `http/export_step_http.py`: open CPACS from XML and export full-aircraft STEP via HTTP.
