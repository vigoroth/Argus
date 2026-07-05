# Argus — Architecture

This document explains how Argus is built and how the pieces connect. It's written for someone reading the codebase for the first time (including future me).

## Design principles

1. **One source of configuration.** Everything that varies between environments — API keys, model names, provider URLs, the database connection — lives in `.env` and is loaded once into a typed `Settings` object (`core/config.py`). No other file reads `os.environ` directly. Change a model or swap providers in `.env`, and the whole app follows.

2. **Provider abstraction.** Nothing in the app constructs an LLM directly. Every component calls `get_llm()` (`core/llm.py`), which returns a model built from settings. Because the layer speaks the OpenAI-compatible protocol, the same code drives OpenAI or a local Ollama model — the only difference is the base URL in `.env`.

3. **One assembly point.** The agent is built in `agent/graph.py`. It imports the provider and every tool and binds them into a single LangGraph loop. Adding a capability means writing a tool and adding it to one list — nothing else changes.

4. **One entry point.** `run_agent()` (`agent/agent_demo.py`) wraps the graph and is the single door used by both the CLI demos and the web server. It also records metrics for every run.

## The agent loop

Argus uses the ReAct pattern (Reason + Act) implemented as a LangGraph state machine:

```
START → llm_node → should_continue? → tools_node → (loop back to llm_node)
                          │
                          └─ no tool call → END (final answer)
```

- `llm_node` calls the model (with all tools bound) on the conversation so far.
- `should_continue` inspects the model's reply: if it requested a tool, route to `tools_node`; otherwise finish.
- `tools_node` (LangGraph's `ToolNode`) executes the requested tool and feeds the result back.

State is a message list with an `add_messages` reducer, so each step appends to the running history.

## Tools

Tools are plain Python functions decorated with `@tool`. The decorator builds the JSON schema the model needs to discover and call them. Each tool returns a string (errors as `"ERROR: ..."` so the agent can recover). Current tools: file read/write, list directory, run shell, web search, document search (RAG), and save/load long-term memory.

Tool *descriptions* are prompts. They tell the model when to use each tool — and, critically, when not to (e.g. web search is steered away from the user's own documents). Getting these boundaries right is most of agent reliability.

## RAG pipeline

**Ingestion** (offline): documents are loaded, chunked (recursive or semantic), embedded, and stored in pgvector along with a Postgres full-text (`tsvector`) column.

**Retrieval** (query time):
1. The LLM expands the question into several focused queries (`query_rewrite.py`).
2. Each query runs dense (pgvector) and sparse (full-text) search (`hybrid.py`).
3. Results are merged with Reciprocal Rank Fusion — `score = Σ 1/(k + rank)` across methods.
4. The fused pool is reranked by a cross-encoder that reads the query and each chunk together (`rerank.py`).
5. The top chunks are returned numbered and sourced for citation.

This is exposed to the agent as a single `search_documents` tool — the whole pipeline lives behind one function call.

## Memory

Two independent layers, both keyed by conversation id:

- **Short-term** — a LangGraph SQLite checkpointer persists the agent's working state per `thread_id`. Reopening a conversation reloads its history into the loop, so the agent remembers earlier turns.
- **Long-term** — a Postgres key-value table (`user_memory`) holds durable facts. The agent writes to it (`save_memory`) when it learns something lasting, and reads from it (`load_memory`) for context. Survives across all sessions.

The web layer separately persists conversations and messages in Postgres for the sidebar — display history, distinct from the agent's working memory.

## Web layer

`web/server.py` is an async FastAPI app:
- `GET /` serves the chat UI.
- `POST /chat` streams the agent's reply token-by-token over Server-Sent Events, while persisting both the user message and the assistant reply, and using the conversation id as the checkpointer thread id.
- `GET /conversations` and `GET /conversations/{id}` power the sidebar.

Streaming works by calling `graph.stream(..., stream_mode="messages")` with a streaming-enabled LLM, forwarding each chunk as an SSE event.

## Observability

`core/metrics.py` provides a `track()` context manager that times a block and records duration, tokens, cost, and success/failure to a `run_metrics` table — even on error. `run_agent` wraps every call in it; the web `/chat` path records the same fields inline. `get_stats_summary()` aggregates the table (lifetime totals, 14-day daily series, last-20 runs) and the app's own `/stats` view (`StatsView.tsx`) renders it — this is the live observability surface. A Grafana container ships in Docker Compose for ad-hoc querying of the same table but is not provisioned with dashboards.

## Infrastructure

`docker/docker-compose.yml` runs Postgres (with pgvector) and Grafana. Grafana is unprovisioned — no datasource or dashboards are committed; the app's built-in `/stats` view is the primary metrics surface. The application currently runs in the local Python environment; containerizing the app itself (one-command full stack) is on the roadmap.

## Data flow (one message, end to end)

```
user types in UI
  → POST /chat (FastAPI)
  → run through graph.stream (LangGraph)
      → llm_node picks a tool (e.g. search_documents)
      → tools_node runs the RAG pipeline → result back to llm_node
      → llm_node produces the final answer, streamed token by token
  → SSE streams tokens to the browser (live)
  → user + assistant messages saved to Postgres
  → run metrics recorded → /stats view
```