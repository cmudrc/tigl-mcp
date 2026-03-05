"""Export STEP CAD through the MCP HTTP endpoint using JSON-RPC over SSE."""

from __future__ import annotations

import base64
import json
import os
import sys

import requests

MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT", "http://127.0.0.1:8000/mcp")
CPACS_PATH = os.environ["CPACS_PATH"]
OUTPUT_PATH = os.environ.get("OUT", "aircraft.step")


if not OUTPUT_PATH.lower().endswith((".step", ".stp")):
    OUTPUT_PATH = f"{OUTPUT_PATH}.step"


def _create_headers() -> dict[str, str]:
    response = requests.get(
        MCP_ENDPOINT,
        headers={"Accept": "application/json, text/event-stream"},
        timeout=2,
    )
    session_id = response.headers.get("mcp-session-id")
    if not session_id:
        print("Missing mcp-session-id header", file=sys.stderr)
        print(dict(response.headers), file=sys.stderr)
        raise SystemExit(1)

    return {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "mcp-session-id": session_id,
    }


def _post_json(
    payload: dict[str, object], headers: dict[str, str]
) -> dict[str, object]:
    response = requests.post(
        MCP_ENDPOINT,
        headers=headers,
        data=json.dumps(payload),
        timeout=60,
    )
    lines = [line for line in response.text.splitlines() if line.startswith("data: ")]
    if not lines:
        print("No SSE data lines", file=sys.stderr)
        print(response.text, file=sys.stderr)
        raise SystemExit(1)
    return json.loads(lines[-1][6:])


def _call_tool(
    headers: dict[str, str],
    tool_name: str,
    arguments: dict[str, object],
    request_id: int,
) -> dict[str, object]:
    response = _post_json(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
        headers,
    )
    result = response.get("result", {})
    if isinstance(result, dict) and result.get("isError"):
        print(json.dumps(response, indent=2), file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(result, dict):
        raise SystemExit("Unexpected response from server")

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured

    content = result.get("content")
    if isinstance(content, list) and content:
        text = content[0].get("text")
        if isinstance(text, str):
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed

    raise SystemExit(f"Could not parse tool response for {tool_name}")


def main() -> None:
    """Open CPACS and export STEP through a running MCP HTTP endpoint."""
    headers = _create_headers()

    _post_json(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                    "logging": {},
                },
                "clientInfo": {"name": "py", "version": "0.1"},
            },
        },
        headers,
    )

    cpacs_xml = open(CPACS_PATH, encoding="utf-8").read()
    open_result = _call_tool(
        headers,
        "open_cpacs",
        {"source_type": "xml_string", "source": cpacs_xml},
        request_id=2,
    )
    session_id = open_result.get("session_id")
    if not isinstance(session_id, str):
        raise SystemExit("open_cpacs did not return a string session_id")

    export_result = _call_tool(
        headers,
        "export_configuration_cad",
        {"session_id": session_id, "format": "step"},
        request_id=3,
    )

    cad_base64 = export_result.get("cad_base64")
    if not isinstance(cad_base64, str):
        raise SystemExit("export_configuration_cad did not return cad_base64")

    cad_bytes = base64.b64decode(cad_base64)
    with open(OUTPUT_PATH, "wb") as file_obj:
        file_obj.write(cad_bytes)

    header = cad_bytes[:16].decode("utf-8", "ignore").lstrip()
    if header.startswith("solid"):
        raise SystemExit(f"Output looks like STL, not STEP: {OUTPUT_PATH}")

    print(f"wrote {OUTPUT_PATH} bytes={len(cad_bytes)}")


if __name__ == "__main__":
    main()
