"""Metrics tool — read-only view of Argus's own run telemetry (Upgrade 006).

Reuses the aggregate queries in app.core.metrics; the model never sends SQL.
"""
from langchain_core.tools import tool


@tool
def query_metrics(days: int = 14) -> str:
    """Summarize Argus's own usage metrics: total runs, success rate, latency,
    token counts, cost, and a daily breakdown for the last `days` days.
    Use for questions about the app's usage, spend, or performance.
    """
    try:
        from app.core.metrics import get_stats_summary
        s = get_stats_summary()
    except Exception as e:
        return f"ERROR: metrics unavailable ({e})"
    t = s.get("totals", {})
    lines = [
        f"Totals: {t.get('runs', 0)} runs, success {t.get('success_rate', 0):.0%}, "
        f"avg {t.get('avg_ms', 0):.0f}ms (p95 {t.get('p95_ms', 0):.0f}ms), "
        f"tokens {t.get('input_tokens', 0)}in/{t.get('output_tokens', 0)}out, "
        f"cost ${t.get('cost_usd', 0):.4f}",
        f"Daily (last {days}d):",
    ]
    for d in s.get("daily", [])[-days:]:
        lines.append(f"  {d['day']}: {d['runs']} runs, ${d['cost']:.4f}, "
                     f"avg {d['avg_ms']:.0f}ms")
    recent = s.get("recent", [])[:5]
    if recent:
        lines.append("Recent runs:")
        for r in recent:
            ok = "ok" if r.get("ok") else "FAIL"
            lines.append(f"  {r['ts']} {r['model']} {r['ms']}ms "
                         f"{r['tokens']}tok ${r['cost']:.4f} {ok}")
    return "\n".join(lines)


METRICS_TOOLS = [query_metrics]
