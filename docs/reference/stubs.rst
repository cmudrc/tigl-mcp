Stub-backed CPACS Behavior
==========================

The current package uses deterministic stand-ins from ``tigl_mcp.cpacs``
and ``tigl_mcp.cpacs_stubs`` instead of requiring full TiXI/TiGL
installations.

Why this exists
---------------

- Local development stays lightweight.
- CI remains deterministic.
- Tests can validate payload shapes and workflow contracts without native
  geometry dependencies.

What is intentionally simplified
--------------------------------

- Bounding boxes are derived from component index, not real geometry.
- Sampling and intersections are synthetic but deterministic.
- Mesh and CAD exports are format-like payloads designed for stable testing.

.. automodule:: tigl_mcp.cpacs
   :members:
