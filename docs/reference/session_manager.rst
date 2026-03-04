Session Management
==================

``SessionManager`` stores stub-backed TiXI and TiGL handles in memory and maps
them to UUID-based session identifiers.

Current guarantees
------------------

- Session creation returns an opaque UUID string.
- Missing sessions raise structured ``InvalidSession`` errors.
- Closing a session marks the stored handles as closed and removes the session.

.. automodule:: tigl_mcp.session_manager
   :members:
