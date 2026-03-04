"""Export stubbed mesh and CAD payloads from a sample CPACS session."""

from __future__ import annotations

import base64
import json

from tigl_mcp.session_manager import SessionManager
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
          <wing uid="W1" name="MainWing" span="30.0" area="80.0" symmetry="x-z" />
        </wings>
        <fuselages>
          <fuselage uid="F1" name="Fuse" length="25.0" />
        </fuselages>
      </model>
    </aircraft>
  </vehicles>
</cpacs>
""".strip()


def main() -> None:
    """Run stub exports and print a stable JSON summary."""
    manager = SessionManager()
    tools = {tool.name: tool for tool in build_tools(manager)}

    open_result = tools["open_cpacs"].handler(
        {"source_type": "xml_string", "source": SAMPLE_CPACS_XML}
    )
    session_id = open_result["session_id"]

    mesh_result = tools["export_component_mesh"].handler(
        {"session_id": session_id, "component_uid": "W1", "format": "stl"}
    )
    cad_result = tools["export_configuration_cad"].handler(
        {"session_id": session_id, "format": "step"}
    )
    tools["close_cpacs"].handler({"session_id": session_id})

    payload = {
        "mesh_prefix": base64.b64decode(mesh_result["mesh_base64"])
        .decode("ascii")
        .splitlines()[0],
        "cad_prefix": base64.b64decode(cad_result["cad_base64"])
        .decode("utf-8")
        .split(":", 2)[:2],
        "num_triangles": mesh_result["num_triangles"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
