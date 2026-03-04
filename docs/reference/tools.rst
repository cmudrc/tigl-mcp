Tool Catalog
============

The current tool catalog is assembled by ``tigl_mcp.tools.build_tools``.

Available tool groups
---------------------

- CPACS lifecycle: ``open_cpacs``, ``close_cpacs``
- Configuration inspection: ``get_configuration_summary``,
  ``list_geometric_components``, ``get_component_metadata``
- Metrics: ``get_wing_summary``, ``get_fuselage_summary``
- Sampling and intersections: ``sample_component_surface``,
  ``intersect_with_plane``, ``intersect_components``
- Exports: ``export_component_mesh``, ``export_configuration_cad``
- Parameter editing: ``get_high_level_parameters``, ``set_high_level_parameters``

All tools use Pydantic-backed request validation and return JSON-serializable
payloads suitable for MCP clients.

.. automodule:: tigl_mcp.tools
   :members:
