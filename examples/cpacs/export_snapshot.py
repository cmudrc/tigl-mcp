"""Inspect a CPACS session and attempt real mesh and CAD exports.

This example prints what the server can state from the file alone, then tries
the two export paths. Both exports require a real TiGL kernel: native
``tigl3``/``tixi3`` bindings, or the ``tigl-mcp:dev`` Docker image. When
neither is reachable the tools raise a structured error, which this example
reports rather than hiding. Nothing here fabricates geometry.
"""

from __future__ import annotations

import base64
import json

from tigl_mcp.errors import MCPError
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tooling import ToolDefinition
from tigl_mcp.tools import build_tools

SAMPLE_CPACS_XML = """
<cpacs>
  <header>
    <creator>Example</creator>
    <description>Example CPACS payload</description>
  </header>
  <vehicles>
    <aircraft>
      <model>
        <wings>
          <wing uID="W1" name="MainWing" symmetry="x-z">
            <sections>
              <section uID="W1_sec1" />
              <section uID="W1_sec2" />
            </sections>
            <segments>
              <segment uID="W1_seg1" />
            </segments>
          </wing>
        </wings>
        <fuselages>
          <fuselage uID="F1" name="Fuse">
            <sections>
              <section uID="F1_sec1" />
            </sections>
          </fuselage>
        </fuselages>
      </model>
    </aircraft>
  </vehicles>
</cpacs>
""".strip()


def _attempt(tool: ToolDefinition, payload: dict[str, object]) -> dict[str, object]:
    """Call a tool, reporting either its byte count or its structured error."""
    try:
        result = tool.handler(payload)
    except MCPError as error:
        detail = error.to_dict()["error"]
        return {"status": "unavailable", "error_type": detail["type"]}

    key = "mesh_base64" if "mesh_base64" in result else "cad_base64"
    return {
        "status": "exported",
        "bytes": len(base64.b64decode(str(result[key]))),
        "source": result.get("source", "tigl"),
    }


def main() -> None:
    """Print a stable JSON summary of parsed facts and export outcomes."""
    manager = SessionManager()
    tools = {tool.name: tool for tool in build_tools(manager)}

    open_result = tools["open_cpacs"].handler(
        {"source_type": "xml_string", "source": SAMPLE_CPACS_XML}
    )
    session_id = open_result["session_id"]

    summary = tools["get_configuration_summary"].handler({"session_id": session_id})
    metadata = tools["get_component_metadata"].handler(
        {"session_id": session_id, "component_uid": "W1"}
    )

    payload = {
        # Read straight from the file, so these are always available.
        "wing_count": len(summary["wings"]),
        "fuselage_count": len(summary["fuselages"]),
        "wing_sections": metadata["wing_data"]["num_sections"],
        "wing_segments": metadata["wing_data"]["num_segments"],
        # Absent unless a real kernel supplied it; never estimated.
        "bounding_box": summary["bounding_box"],
        # Require a real kernel, so these may report as unavailable.
        "mesh": _attempt(
            tools["export_component_mesh"],
            {"session_id": session_id, "component_uid": "W1", "format": "stl"},
        ),
        "cad": _attempt(
            tools["export_configuration_cad"],
            {"session_id": session_id, "format": "step"},
        ),
    }

    tools["close_cpacs"].handler({"session_id": session_id})
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
