"""Every tool's output schema must be absent or a JSON object schema.

Kiro IDE 1.4.5 rejected the whole aircraft gateway because tigl tools
declared ``{}`` or ``{"success": "boolean"}`` as their output schema.
"""

from tigl_mcp.fastmcp_adapter import _output_schema, to_fastmcp_tools
from tigl_mcp.session_manager import SessionManager
from tigl_mcp.tools import build_tools


def test_every_output_schema_is_none_or_object() -> None:
    tools = to_fastmcp_tools(build_tools(SessionManager()))
    assert tools
    for tool in tools:
        schema = tool.output_schema
        assert schema is None or schema.get("type") == "object", tool.name


def test_placeholders_are_dropped_and_real_schemas_kept() -> None:
    assert _output_schema({}) is None
    assert _output_schema({"success": "boolean"}) is None
    assert _output_schema(None) is None
    real = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    assert _output_schema(real) == real
