# Argus

A self-hosted, local-first AI agent workspace built from scratch — tool-using agents, advanced retrieval-augmented generation (RAG), persistent memory, web search, Model Context Protocol (MCP) integration, multi-provider model selection, a password-protected streaming chat UI, an evaluation harness, and full observability. Runs on cloud models (OpenAI) or fully offline on local models (Ollama).

**Version 1.3**

---

## What it does

Argus is an autonomous AI agent that can:

- **Reason and act in a loop** — a LangGraph ReAct agent (fully async) that decides when to call tools, reads the results, and continues until it can answer.
- **Switch models and providers from the UI** — pick a provider (OpenAI or Ollama) and a specific model per conversation from a two-step selector; the model list is fetched live from each provider, never hardcoded. Anthropic and Google Gemini are wired and activate when their API keys are added.
- **Connect to the MCP ecosystem** — integrates external Model Context Protocol servers (filesystem, web fetch) alongside its own tools, all through one async agent loop. Tools are curated to keep selection sharp.
- **Search and fetch the web** — `web_search` (DuckDuckGo, no API key) to find pages; the MCP `fetch` server to read a specific URL.
- **Answer from your own documents** — advanced RAG: hybrid search (semantic + keyword), Reciprocal Rank Fusion, cross-encoder reranking, and LLM query expansion, with citations.
- **Remember you** — short-term conversation memory (per thread), long-term memory (Postgres), plus a knowledge-graph memory: conversations are written to an Obsidian vault and graphify builds a queryable graph over them, exposed to the agent through the native `graph_query` tool. Memory is verified by an eval harness.
- **Be protected** — the web UI sits behind a username + password login gate (bcrypt-hashed credentials, signed session cookies).
- **Monitor itself** — every run records latency, tokens, cost, and success to Postgres, surfaced in the built-in `/stats` dashboard.
- **Chat like a real app** — streaming web UI with a conversation sidebar; past chats persist and reopen.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Web UI (login-gated streaming chat + conversation list)  │
│     FastAPI · SSE streaming · provider/model selector     │
│     bcrypt auth + signed session cookies                  │
├──────────────────────────────────────────────────────────┤
│  Agent core (async LangGraph ReAct loop)                  │
│     ├─ Provider layer: OpenAI · Ollama · Anthropic ·      │
│     │                   Gemini (per-request selectable)   │
│     ├─ Built-in tools: shell · web search · document      │
│     │        search (RAG) · memory · graph_query          │
│     └─ MCP tools (config-driven, curated allowlist)       │
├──────────────────────────────────────────────────────────┤
│  MCP servers (stdio subprocesses)                         │
│     ├─ fetch        — read web pages                      │
│     └─ filesystem   — file read/write/search/edit         │
├──────────────────────────────────────────────────────────┤
│  Advanced RAG: expand → hybrid (dense+sparse) → RRF       │
│                → cross-encoder rerank → cite              │
├──────────────────────────────────────────────────────────┤
│  Memory: short-term (async SQLite checkpointer) · long-   │
│    term (Postgres) · graph (Obsidian vault + graphify,     │
│    queried via the graph_query tool)                      │
├──────────────────────────────────────────────────────────┤
│  Eval harness: single + cross-conversation memory tests   │
│                with per-case timeouts                     │
├──────────────────────────────────────────────────────────┤
│  Observability: per-run metrics → Postgres → /stats view  │
├──────────────────────────────────────────────────────────┤
│  Infra: Docker Compose (Postgres/pgvector + Grafana)      │
└──────────────────────────────────────────────────────────┘
```

---

## Multi-provider model selection

Argus abstracts every model behind a single provider layer (`get_llm`). The web UI exposes this as a two-step selector: choose a **provider**, then a **model** from that provider's live-fetched list.

- **OpenAI** — models queried from the OpenAI API, filtered to chat-capable models.
- **Ollama** — models queried from the local Ollama daemon (`/api/tags`); fully offline.
- **Anthropic / Gemini** — provider branches are implemented and activate once `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` are set.

The selection flows per-request through the agent graph, which is cached per provider+model so switching is cheap. Provider and model are decoupled from `.env` — the UI choice overrides the default.

---

## Authentication

The web UI is protected by a single-user login gate:

- Username checked in constant time; password verified against a **bcrypt hash** (never stored in plaintext).
- Sessions use **signed, time-limited cookies** (itsdangerous), httponly.
- All API routes require a valid session; unauthenticated requests are rejected.

Credentials live in `.env` (`ARGUS_USERNAME`, `ARGUS_PASSWORD_HASH`, `ARGUS_SESSION_SECRET` — legacy `NEXUS_*` names still work as a fallback) — only the hash is stored, so the password is never recoverable from disk.

---

## Evaluation harness

Memory is measured, not assumed. The eval harness (`app/eval/`) runs:

- **Single-conversation recall** — a fact stated and recalled within one thread (checkpointer memory).
- **Cross-conversation recall** — a fact saved in one conversation and recalled in a separate one (long-term Postgres memory).

Each case has a per-case timeout so a stuck run fails cleanly rather than hanging. The current Postgres-memory baseline passes all cases (8/8). The harness is the basis for benchmarking memory backends against each other.

### Unit tests

Fast, service-free unit tests (pricing, config, chunking, RRF fusion, auth, provider dispatch) live in `tests/` and run without Postgres or API keys:

```bash
pip install -e . --group dev   # pytest/ruff
pytest                         # unit suite (DB-dependent tests skip if psycopg absent)
ruff check .
```

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| Agent framework | LangChain + LangGraph (async) |
| Providers | OpenAI · Ollama · Anthropic · Google Gemini (via a unified provider layer) |
| MCP | langchain-mcp-adapters (fetch, filesystem) |
| Vector store | Postgres + pgvector |
| Retrieval | Hybrid (pgvector + Postgres FTS) + RRF + cross-encoder rerank + query expansion |
| Web search | DuckDuckGo (`ddgs`) |
| Memory | LangGraph async SQLite checkpointer (short) · Postgres (long) · Obsidian vault + graphify graph (MCP) |
| Web backend | FastAPI + SSE (async) |
| Auth | bcrypt + itsdangerous signed cookies |
| Observability | Custom metrics → Postgres → built-in `/stats` view (Grafana available, unprovisioned) |
| Infrastructure | Docker Compose |

---

## Quick start

### Prerequisites
- Python 3.11+, Docker
- Node.js 20+ and `uv` (for MCP servers)
- OpenAI API key (optional if running fully local with Ollama)

### Setup
```bash
git clone https://github.com/vigoroth/Argus.git
cd Argus
conda create -n argus python=3.11 -y
conda activate argus
pip install -e .          # all runtime deps from pyproject.toml
# pip install -e . --group dev   # + pytest/ruff for development
cp .env.example .env
git config core.hooksPath .githooks   # enable repo hooks (blocks AI-attribution trailers)
```

### Configure `.env`
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+psycopg://argus:argus_dev_pw@localhost:5434/argus
# auth (legacy NEXUS_* names still work as a fallback)
ARGUS_USERNAME=your-name
ARGUS_PASSWORD_HASH=<bcrypt hash>      # python -c "import bcrypt;print(bcrypt.hashpw(b'pw',bcrypt.gensalt()).decode())"
ARGUS_SESSION_SECRET=<random hex>      # python -c "import secrets;print(secrets.token_hex(32))"
# optional providers
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
```

### Infrastructure
```bash
docker compose -f docker/docker-compose.yml up -d
# Postgres (pgvector) on :5434, Grafana on http://localhost:3001

docker exec argus_pg psql -U argus -d argus -c "
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE IF EXISTS langchain_pg_embedding
  ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', document)) STORED;
CREATE INDEX IF NOT EXISTS idx_fts ON langchain_pg_embedding USING GIN (fts);
"
```

### MCP servers (optional but recommended)
```bash
# fetch + filesystem need no install (uvx/npx fetch on first use)
# servers are declared in mcp_servers.json (uvx/npx resolve on first use; client fail-softs if missing)
```

### Knowledge graph (graphify + Obsidian vault)
```bash
pipx install graphifyy              # the graphify CLI
pipx inject graphifyy openai        # semantic extraction needs the openai client
mkdir -p "$ARGUS_VAULT_PATH"        # vault graphify indexes (default ~/vault)
```
Conversations are written to `$ARGUS_VAULT_PATH` and re-indexed on each turn by
`refresh_graph` (`app/web/vault_writer.py`), which shells out to `graphify extract`.
That build calls an LLM, so `OPENAI_API_KEY` must be set in `.env` — the extract
subprocess inherits the app's environment. The agent reads the graph via the
`graph_query` tool; the 3D graph view reads it from the `/graph` endpoint.

### Frontend (React + Vite, Odysseus design)
```bash
cd app/web/frontend
npm install
npm run build        # → dist/, served by FastAPI at /
# dev mode with hot reload (proxies API to :8000):
npm run dev
```

### Run
```bash
python -m app.rag.ingest_demo      # ingest a document
python -m app.eval.runner          # run the memory eval harness
python -m app.web.server           # launch chat UI at http://127.0.0.1:8000 (login required)
```
The server binds **127.0.0.1** by default because the built-in Terminal is a real
shell on the host (login-gated). Set `ARGUS_BIND=0.0.0.0` to expose on the LAN —
only with strong credentials.

---

## Running fully local (Ollama)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:8b
```
Then in the UI, pick **Ollama** as the provider and select the model. No code or `.env` changes needed — the selector routes to the local daemon automatically.

---

## Roadmap

- [x] MCP integration (fetch, filesystem)
- [x] Tool curation (allowlist to keep selection reliable)
- [x] Multi-provider support + per-conversation model selector
- [x] Login gate (bcrypt + signed sessions)
- [x] Eval harness (single + cross-conversation memory)
- [x] Auto-memory: remember conversations and recall context automatically
- [x] Obsidian vault + graphify knowledge graph, queried via the graph_query tool
- [x] Encrypted API-key dashboard (write-only, login-gated; keys applied live)
- [x] Activity log (tool calls / results streamed live and persisted per conversation)
- [x] Conversation summarization for long threads (running summary + checkpoint pruning)
- [ ] Containerize the app itself (one-command full stack)

---

## Contributors

- [Nick.Kantiotis](https://github.com/vigoroth) — sole author/contributor

---

## License

MIT