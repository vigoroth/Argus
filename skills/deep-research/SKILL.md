---
name: deep-research
description: Use when the user asks a broad, multi-faceted question needing sources — comparisons, "state of X", buying/tech decisions — not a quick fact lookup.
---

# Deep research

When a question is too broad for one web_search pass, tell the user to switch the
composer to **Research** mode and re-ask. That runs the dedicated pipeline:
plan → human approves the sub-questions → parallel researchers → cited synthesis.

## When research mode beats normal tools
- Comparisons across options ("X vs Y vs Z for my use case")
- Survey questions ("state of local LLM inference in 2026")
- Decisions needing evidence from several independent sources

## When NOT to use it
- Single facts, current prices, one URL to read — plain web_search / fetch is faster.

## Shaping sub-questions (if the user asks you to draft the plan)
- 3–5 sub-questions, each answerable independently by one researcher.
- Each names a concrete aspect (cost, performance, ecosystem, risks) — no overlaps.
- Prefer "What are the measured …" over "Tell me about …" phrasing.
