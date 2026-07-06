---
name: brainstorm
description: Use when the user wants new ideas for improving Argus or another project — generates candidate upgrades and records accepted ones in the backlog.
---

# Brainstorm

Generate upgrade ideas grounded in evidence, not vibes — then bank them.

1. Restate the goal area ("improve RAG quality", "reduce cost").
2. Gather grounding: web_search recent practice; search_documents / graph_query for
   what the project already does; note gaps.
3. Produce 5–10 ideas as a table: | Idea | Category | Why it's worth learning | Effort |
   — categories: systems/security/ml/frontend/devops/agent/rag/perf; effort
   small/medium/large.
4. Rank by learning-value ÷ effort. Flag the top 2 as recommended.
5. Ask which ideas to keep. For EACH accepted idea call
   `add_idea(idea, category, why, effort)` — it appends to the private lab backlog
   (lab/IDEAS.md). Confirm what was recorded.

Broad topic + user wants sources → suggest Research mode with the ideas question,
then run steps 3–5 on the research report.
