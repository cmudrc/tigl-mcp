CLI and Transports
==================

The ``tigl-mcp-server`` command and ``python -m tigl_mcp_server`` entrypoint
both use ``tigl_mcp_server.main``.

Supported transports
--------------------

- ``stdio`` for editor and local MCP integrations
- ``http`` for HTTP-based serving
- ``sse`` for server-sent events
- ``streamable-http`` for FastMCP streamable HTTP mode

The parser defaults to ``stdio`` and only applies ``host``, ``port``, and
``path`` when an HTTP-compatible transport is selected.
