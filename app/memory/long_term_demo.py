"""Module 6b demo: long-term memory across separate agent runs.

Run:  python -m app.memory.long_term_demo
"""
from app.memory.long_term import init_memory_table
from app.agent.agent_demo import run_agent


def main() -> None:
    init_memory_table()

    print("=== SESSION 1: tell it something durable ===")
    print(run_agent("Remember that I'm job hunting for ML roles in Athens, Greece."))

    print("\n=== SESSION 2: brand new run, no shared thread ===")
    print(run_agent("Based on what you know about me, where am I looking for work?"))


if __name__ == "__main__":
    main()