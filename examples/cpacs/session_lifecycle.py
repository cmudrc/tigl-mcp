"""Open a sample CPACS document, inspect it, and close the session."""

from __future__ import annotations

import json

from tigl_mcp_server.session_manager import SessionManager
from tigl_mcp_server.tools import build_tools

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
    """Run the deterministic session lifecycle and print a JSON summary."""
    manager = SessionManager()
    tools = {tool.name: tool for tool in build_tools(manager)}

    open_result = tools["open_cpacs"].handler(
        {"source_type": "xml_string", "source": SAMPLE_CPACS_XML}
    )
    session_id = open_result["session_id"]
    summary = tools["get_configuration_summary"].handler({"session_id": session_id})
    close_result = tools["close_cpacs"].handler({"session_id": session_id})

    payload = {
        "session_opened": True,
        "session_closed": close_result["success"],
        "wing_ids": [wing["uid"] for wing in summary["wings"]],
        "fuselage_ids": [fuselage["uid"] for fuselage in summary["fuselages"]],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
