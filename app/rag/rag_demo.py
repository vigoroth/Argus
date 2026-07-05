"""Module 5 demo: retrieval alone, then the agent using RAG.

Run:  python -m app.rag.rag_demo
"""
from app.agent.agent_demo import run_agent
from app.rag.retriever import search


def main() -> None:
    print("=== RAW RETRIEVAL ===")
    for r in search("How do I get a job through referrals?"):
        print(f"score={r['score']}  {r['text'][:80]}...")

    print("\n=== AGENT USING RAG ===")
    answer = run_agent(
        "What advice do I have about networking and referrals when job hunting?"
    )
    print(answer)


if __name__ == "__main__":
    main()