"""Module 3 demo: the agent loop in action.

Run:  python -m app.agent.agent_demo
"""
from langchain_core.messages import HumanMessage
from app.agent.graph import build_graph
import asyncio
from app.core.metrics import track
from app.core.pricing import cost_usd
from app.core.config import get_settings

async def run_agent(user_input: str) -> str:
    graph = await build_graph()
    with track("agent_run") as m:
        result = await graph.ainvoke({"messages": [HumanMessage(content=user_input)]})
        for msg in result["messages"]:
            usage = getattr(msg, "usage_metadata", None)
            if usage:
                m["input_tokens"] += usage.get("input_tokens", 0)
                m["output_tokens"] += usage.get("output_tokens", 0)
        m["cost_usd"] = cost_usd(get_settings().llm_model, m["input_tokens"], m["output_tokens"])
    return result["messages"][-1].content

def main() -> None:
    import asyncio

    async def run_all():
        print("=== TEST 1: no tools ===")
        print(await run_agent("What is the capital of Greece?"))

        print("\n=== TEST 2: MCP fetch tool ===")
        print(await run_agent("Fetch https://example.com and summarize it in one sentence."))

        print("\n=== TEST 3: shell tool ===")
        print(await run_agent("How many lines are in /tmp/jobs.txt?"))

    asyncio.run(run_all())


if __name__ == "__main__":
    main()
