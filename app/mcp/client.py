"""Load tools from configured MCP servers (config-driven, resilient, curated)."""
import json
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

CONFIG_PATH = Path(__file__).parent.parent.parent / "mcp_servers.json"

# Curate which tools to keep per server. A server NOT listed here = keep all its tools.
# A server listed here = keep only the named tools.
# filesystem: read-only subset — the agent has no business writing/moving files on
# the host through MCP, and fewer tools keeps selection sharp.
MCP_TOOL_ALLOWLIST = {
    "filesystem": {
        "read_text_file",
        "read_multiple_files",
        "list_directory",
        "directory_tree",
        "search_files",
        "get_file_info",
    },
}


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"WARNING: {CONFIG_PATH} not found")
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text())
    except Exception as e:
        print(f"WARNING: could not read {CONFIG_PATH}: {e}")
        return {}


async def load_mcp_tools() -> list:
    servers = _load_config()
    if not servers:
        return []
    all_tools = []
    for name, cfg in servers.items():
        try:
            client = MultiServerMCPClient({name: cfg})
            tools = await client.get_tools()
            # apply allowlist if this server has one
            allow = MCP_TOOL_ALLOWLIST.get(name)
            if allow is not None:
                tools = [t for t in tools if t.name in allow]
            print(f"MCP '{name}': loaded {len(tools)} tools")
            all_tools.extend(tools)
        except Exception as e:
            print(f"MCP '{name}' FAILED: {type(e).__name__}: {str(e)[:200]}")
    return all_tools