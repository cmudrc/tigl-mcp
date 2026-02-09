import os, json, base64, sys, requests

MCP = "http://127.0.0.1:8000/mcp"
CPACS_PATH = os.environ["CPACS_PATH"]
COMP_UID = os.environ.get("COMP_UID", "wing_1")
OUT = os.environ.get("OUT", f"{COMP_UID}.stl")

# 1) get MCP session id (FastMCP uses response header)
r = requests.get(MCP, headers={"Accept": "application/json, text/event-stream"}, timeout=2)
sid = r.headers.get("mcp-session-id")
if not sid:
    print("Missing mcp-session-id header. Raw headers:", dict(r.headers))
    sys.exit(1)
print("SID =", sid)

headers = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "mcp-session-id": sid,
}

def post_json(payload: dict) -> dict:
    rr = requests.post(MCP, headers=headers, data=json.dumps(payload), timeout=60)
    # Server returns SSE; last 'data: {...}' line is the JSON-RPC object
    lines = [ln for ln in rr.text.splitlines() if ln.startswith("data: ")]
    if not lines:
        print("No SSE data lines. Raw response:\n", rr.text)
        sys.exit(1)
    return json.loads(lines[-1][6:])

# 2) initialize
resp = post_json({
    "jsonrpc":"2.0","id":1,"method":"initialize",
    "params":{
        "protocolVersion":"2024-11-05",
        "capabilities":{"tools":{},"resources":{},"prompts":{},"logging":{}},
        "clientInfo":{"name":"py","version":"0.1"}
    }
})
print("initialize:", resp["result"]["serverInfo"])

# 3) open_cpacs (xml_string to avoid host/container path issues)
xml = open(CPACS_PATH, "r", encoding="utf-8").read()
resp = post_json({
    "jsonrpc":"2.0","id":2,"method":"tools/call",
    "params":{"name":"open_cpacs","arguments":{"source_type":"xml_string","source": xml}}
})
res = resp.get("result", {})
if res.get("isError"):
    print("open_cpacs ERROR:", json.dumps(resp, indent=2))
    sys.exit(1)

sc = res.get("structuredContent") or {}
session_id = sc.get("session_id")
if not session_id:
    # some servers also mirror as JSON string in content[0].text
    session_id = json.loads(res["content"][0]["text"])["session_id"]
print("SESSION_ID =", session_id)

# 4) list components
resp = post_json({
    "jsonrpc":"2.0","id":3,"method":"tools/call",
    "params":{"name":"list_geometric_components","arguments":{"session_id": session_id}}
})
res = resp.get("result", {})
if res.get("isError"):
    print("list_geometric_components ERROR:", json.dumps(resp, indent=2))
    sys.exit(1)
sc = res.get("structuredContent") or {}
comps = [c["uid"] for c in sc.get("components", [])]
print("components:", comps)

# 5) export STL
resp = post_json({
    "jsonrpc":"2.0","id":4,"method":"tools/call",
    "params":{"name":"export_component_mesh","arguments":{
        "session_id": session_id,
        "component_uid": COMP_UID,
        "format": "stl"
    }}
})
res = resp.get("result", {})
if res.get("isError"):
    print("export_component_mesh ERROR:", json.dumps(resp, indent=2))
    sys.exit(1)

sc = res.get("structuredContent") or {}
b64 = sc.get("mesh_base64")
if not b64:
    # fallback if server only puts JSON string in content text
    b64 = json.loads(res["content"][0]["text"])["mesh_base64"]

data = base64.b64decode(b64)
open(OUT, "wb").write(data)
print("wrote", OUT, "bytes=", len(data))
print("head:", data[:80])
