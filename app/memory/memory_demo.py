"""Module 6 demo: short-term conversation memory via checkpointer.

Run:  python -m app.memory.memory_demo
"""
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver

from app.agent.graph import build_graph


def main() -> None:
    # SqliteSaver persists state to a file; same thread_id resumes history
    with SqliteSaver.from_conn_string("data/memory.sqlite") as saver:
        graph = build_graph(checkpointer=saver)
        config = {"configurable": {"thread_id": "demo-thread-1"}}

        print("=== TURN 1 ===")
        r1 = graph.invoke(
            {"messages": [HumanMessage(
                content="My name is Vigoroth and I'm job hunting for ML roles."
            )]},
            config=config,
        )
        print(r1["messages"][-1].content)

        print("\n=== TURN 2 (same thread, should remember) ===")
        r2 = graph.invoke(
            {"messages": [HumanMessage(content="What's my name and what am I looking for?")]},
            config=config,
        )
        print(r2["messages"][-1].content)


if __name__ == "__main__":
    main()