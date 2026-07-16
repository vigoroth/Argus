"""Hook-aware replacement for LangGraph's ToolNode (Upgrade 009).

Same contract — read tool_calls off the last AI message, return ToolMessages —
but every call passes through the pre_tool_use gate (blockable) and
post_tool_use observers (always). The model sees a block as an ordinary tool
result, so it can explain and adapt instead of crashing the turn.
"""
import time

from langchain_core.messages import ToolMessage

from app.hooks.registry import run_post_tool_use, run_pre_tool_use


def make_hooked_tool_node(tools: list):
    tool_map = {t.name: t for t in tools}

    async def tools_node(state) -> dict:
        last = state["messages"][-1]
        results = []
        for tc in getattr(last, "tool_calls", []) or []:
            name, args, tcid = tc["name"], tc.get("args") or {}, tc["id"]

            reason = run_pre_tool_use(name, args)
            if reason:
                run_post_tool_use(name, args, reason, 0.0)
                results.append(ToolMessage(content=reason, tool_call_id=tcid, name=name))
                continue

            t0 = time.perf_counter()
            try:
                tool_obj = tool_map.get(name)
                if tool_obj is None:
                    out = f"ERROR: unknown tool {name!r}"
                elif getattr(tool_obj, "coroutine", None) is None:
                    # Avoid LangChain's default-executor bridge for synchronous
                    # tools. On Python 3.13 that executor can prevent the event
                    # loop from shutting down after an otherwise completed run.
                    out = tool_obj.invoke(args)
                else:
                    out = await tool_obj.ainvoke(args)
            except Exception as e:  # a failing tool never sinks the turn
                out = f"ERROR: {e}"
            ms = (time.perf_counter() - t0) * 1000
            run_post_tool_use(name, args, str(out), ms)
            results.append(ToolMessage(content=str(out), tool_call_id=tcid, name=name))
        return {"messages": results}

    return tools_node
