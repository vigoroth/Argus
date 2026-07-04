"""Module 1 demo: the tracked provider call.

Run:  python -m app.core.llm_demo
"""

from app.core.llm import invoke_tracked


def main() -> None:
    result = invoke_tracked(
        "In one sentence, what is retrieval-augmented generation?",
        system="You are a concise technical assistant.",
    )
    print("\n--- OUTPUT ---")
    print(result.text)
    print("\n--- ACCOUNTING ---")
    print(f"input={result.input_tokens}  output={result.output_tokens}  cost=${result.cost_usd:.6f}")


if __name__ == "__main__":
    main()