"""Step 1: prove the MCP adapter works in isolation, before touching the graph.

Connects to the 'fetch' MCP server (reads web pages), lists its tools,
and calls one. No agent, no graph — just the raw connection.

Run:  python -m app.mcp.mcp_test
"""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient


async def main() -> None:
    client = MultiServerMCPClient(
        {
            "fetch": {
                "transport": "stdio",
                "command": "uvx",
                "args": ["mcp-server-fetch"],
            }
        }
    )

    # pull the server's tools, converted to LangChain tools
    tools = await client.get_tools()

    print(f"Connected. {len(tools)} tool(s) from 'fetch':")
    for t in tools:
        print(f"  · {t.name}: {t.description[:70]}")

    # call one tool directly to prove it works
    fetch_tool = tools[0]
    print(f"\nCalling {fetch_tool.name}...")
    result = await fetch_tool.ainvoke({"url": "https://example.com"})
    print("Result (first 200 chars):")
    print(str(result)[:200])


if __name__ == "__main__":
    asyncio.run(main())