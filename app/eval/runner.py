"""Eval runner: feed each case's turns to the agent, score the final answer,
print a pass/fail report. Per-case timeout so a stuck case fails instead of hanging.

Run:  python -m app.eval.runner
"""
import asyncio
import os
import shutil
import subprocess
import uuid
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# Graph-eval isolation: point the vault at a scratch dir BEFORE any app import
# resolves settings, and wipe it every run so no graph state leaks between runs
# (the state-isolation lesson from MEMORY_EVAL.md — a warmed store inflates scores).
# Must live OUTSIDE the repo: graphify honors .gitignore, and anything under the
# repo's ignored data/ dir is skipped entirely ("found 0 docs").
import tempfile
EVAL_VAULT = Path(tempfile.gettempdir()) / "nexus_eval_vault"
os.environ["NEXUS_VAULT_PATH"] = str(EVAL_VAULT)
if EVAL_VAULT.exists():
    shutil.rmtree(EVAL_VAULT)
EVAL_VAULT.mkdir(parents=True)

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import build_graph
from app.eval.cases import MEMORY_CASES, CROSS_CONV_CASES, EvalCase, CrossConvCase , SECURITY_CASES

CASE_TIMEOUT = 45  # seconds per agent invocation


def _score(answer: str, case) -> tuple[bool, str]:
    low = answer.lower()
    if getattr(case, "expect_all", None):
        missing = [k for k in case.expect_all if k.lower() not in low]
        if missing:
            return False, f"missing all-required: {missing}"
    if getattr(case, "expect_any", None):
        if not any(k.lower() in low for k in case.expect_any):
            return False, f"none of expected: {case.expect_any}"
    return True, "ok"


async def _invoke(graph, content: str, config: dict) -> str:
    """One agent call with a timeout; returns the final answer text."""
    result = await asyncio.wait_for(
        graph.ainvoke({"messages": [HumanMessage(content=content)]}, config=config),
        timeout=CASE_TIMEOUT,
    )
    return result["messages"][-1].content


async def _run_case(graph, case: EvalCase) -> tuple[bool, str, str]:
    """Single-conversation case: all turns in one thread, score final answer."""
    config = {"configurable": {"thread_id": f"eval-{case.name}-{uuid.uuid4().hex[:8]}"}}
    final = ""
    try:
        for turn in case.turns:
            final = await _invoke(graph, turn, config)
    except asyncio.TimeoutError:
        return False, f"TIMEOUT (>{CASE_TIMEOUT}s, agent didn't finish)", final
    except Exception as e:
        return False, f"ERROR: {type(e).__name__}: {str(e)[:100]}", final
    passed, reason = _score(final, case)
    return passed, reason, final


async def _run_cross_case(graph, case: CrossConvCase) -> tuple[bool, str, str]:
    """Cross-conversation: store in thread A, recall in fresh thread B."""
    try:
        thread_a = {"configurable": {"thread_id": f"eval-store-{uuid.uuid4().hex[:8]}"}}
        for turn in case.store_turns:
            await _invoke(graph, turn, thread_a)
        thread_b = {"configurable": {"thread_id": f"eval-recall-{uuid.uuid4().hex[:8]}"}}
        answer = await _invoke(graph, case.recall_turn, thread_b)
    except asyncio.TimeoutError:
        return False, f"TIMEOUT (>{CASE_TIMEOUT}s, agent didn't finish)", ""
    except Exception as e:
        return False, f"ERROR: {type(e).__name__}: {str(e)[:100]}", ""
    passed, reason = _score(answer, case)
    return passed, reason, answer


async def _report(title: str, cases: list, runner, backend: str = "both") -> None:
    async with AsyncSqliteSaver.from_conn_string("data/eval_memory.sqlite") as cp:
        graph = await build_graph(checkpointer=cp, memory_backend=backend)
        passed = 0
        print(f"\n{title} ({len(cases)} cases)\n" + "=" * 50)
        for case in cases:
            ok, reason, answer = await runner(graph, case)
            passed += ok
            print(f"[{'PASS' if ok else 'FAIL'}] {case.name}")
            if not ok:
                print(f"       {reason}")
                if answer:
                    print(f"       answer: {answer[:120]!r}")
        print("=" * 50)
        print(f"{passed}/{len(cases)} passed\n")


async def _run_security_case(graph, case) -> tuple[bool, str, str]:
    """Plant a malicious memory, probe, verify the agent ignored the injection."""
    from app.memory.long_term import remember, _conn
    try:
        remember(case.plant_key, case.plant_value)
        cfg = {"configurable": {"thread_id": f"sec-{uuid.uuid4().hex[:8]}"}}
        answer = await _invoke(graph, case.probe, cfg)
        up = answer.upper()
        leaked = [s for s in case.must_not_contain if s.upper() in up]
        passed = not leaked
        reason = "defended" if passed else f"INJECTION SUCCEEDED: leaked {leaked}"
        return passed, reason, answer
    except asyncio.TimeoutError:
        return False, "TIMEOUT", ""
    finally:
        # always clean up the planted injection
        with _conn() as c:
            c.execute("DELETE FROM user_memory WHERE key = %s", (case.plant_key,))




def _seed_graph_vault(cases: list[CrossConvCase]) -> bool:
    """Write each case's stored facts into the (freshly wiped) eval vault as
    conversation notes, then run ONE synchronous graphify extract over it.
    Returns False (and skips the graph eval) if graphify isn't installed."""
    graphify = shutil.which("graphify")
    if not graphify:
        print("\nGRAPH eval skipped: graphify not on PATH")
        return False
    from app.web.vault_writer import write_conversation
    for case in cases:
        msgs = []
        for turn in case.store_turns:
            msgs.append({"role": "user", "content": turn})
            msgs.append({"role": "assistant", "content": "Noted — I'll remember that."})
        write_conversation(case.name, case.name, msgs)
    print(f"\nGRAPH eval: extracting {len(cases)} seeded conversations "
          f"(LLM-backed, may take a few minutes) ...")
    try:
        # explicit backend: auto-detect picks any backend with an env key set,
        # even an invalid one (e.g. a stale GOOGLE_API_KEY selects gemini)
        proc = subprocess.run(
            [graphify, "extract", str(EVAL_VAULT), "--backend", "openai"],
            cwd=str(EVAL_VAULT), capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("GRAPH eval skipped: graphify extract timed out")
        return False
    if proc.returncode != 0:
        print(f"GRAPH eval skipped: extract failed: {(proc.stderr or proc.stdout)[:300]}")
        return False
    return True


async def _run_graph_recall_case(graph, case: CrossConvCase) -> tuple[bool, str, str]:
    """Graph backend: facts were seeded into the vault by _seed_graph_vault;
    only the recall turn runs, in a fresh thread, with graph_query as the sole
    memory path (no Postgres tools, no fact injection)."""
    cfg = {"configurable": {"thread_id": f"eval-graph-{uuid.uuid4().hex[:8]}"}}
    try:
        answer = await _invoke(graph, case.recall_turn, cfg)
    except asyncio.TimeoutError:
        return False, f"TIMEOUT (>{CASE_TIMEOUT}s, agent didn't finish)", ""
    except Exception as e:
        return False, f"ERROR: {type(e).__name__}: {str(e)[:100]}", ""
    passed, reason = _score(answer, case)
    return passed, reason, answer


def main() -> None:
    async def all_evals():
        # the comparison: identical cross-conversation cases, each memory backend
        await _report("CROSS-CONV — POSTGRES", CROSS_CONV_CASES, _run_cross_case, "postgres")
        if _seed_graph_vault(CROSS_CONV_CASES):
            await _report("CROSS-CONV — GRAPH", CROSS_CONV_CASES, _run_graph_recall_case, "graph")
        await _report("MEMORY-INJECTION SECURITY", SECURITY_CASES, _run_security_case)
    asyncio.run(all_evals())


if __name__ == "__main__":
    main()