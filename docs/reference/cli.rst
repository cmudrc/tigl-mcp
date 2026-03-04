CLI and Transports
==================

The ``tigl-mcp`` command and ``python -m tigl_mcp`` entrypoint
both use ``tigl_mcp.main``.

Supported transports
--------------------

- ``stdio`` for editor and local MCP integrations
- ``http`` for HTTP-based serving
- ``sse`` for server-sent events
- ``streamable-http`` for FastMCP streamable HTTP mode

The parser defaults to ``stdio`` and only applies ``host``, ``port``, and
``path`` when an HTTP-compatible transport is selected.
