<div align="center">

<img src="docs/hero.png" alt="Argus" width="150" />

<h1>Argus</h1>

<strong><em>Yours for the voyage.</em></strong> ⛵

<p>A self-hosted, local-first AI agent workspace — built from scratch.<br/>
Tool-using LangGraph agent · deep research · gated self-extension (skills · subagents · tools) · sandboxed shell · advanced RAG · persistent + graph memory · MCP · multi-provider LLMs · streaming web UI · eval harness · full observability.</p>

<p>
  <img src="https://img.shields.io/badge/License-MIT-7C5CF0?style=for-the-badge" alt="License MIT" />
  <img src="https://img.shields.io/badge/Version-1.8-7C5CF0?style=for-the-badge" alt="Version 1.8" />
  <img src="https://img.shields.io/badge/Tests-143%20passing-7C5CF0?style=for-the-badge" alt="Tests 143 passing" />
  <img src="https://img.shields.io/github/actions/workflow/status/vigoroth/Argus/ci.yml?branch=main&style=for-the-badge&label=CI&color=7C5CF0" alt="CI" />
  <img src="https://img.shields.io/badge/Local--first-100%25-7C5CF0?style=for-the-badge" alt="Local-first" />
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/LangGraph-1C3C3C?style=for-the-badge&logo=langgraph&logoColor=white" alt="LangGraph" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="pgvector" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" />
</p>

</div>

---

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Multi-provider model selection](#multi-provider-model-selection)
- [Authentication](#authentication)
- [Evaluation harness](#evaluation-harness)
- [Tech stack](#tech-stack)
- [Quick start](#quick-start)
- [Running fully local (Ollama)](#running-fully-local-ollama)
- [Roadmap](#roadmap)
- [About the author](#about-the-author)
- [License](#license)

---

## What it does

Argus is an autonomous AI agent that can:

- **Reason and act in a loop** — a LangGraph ReAct agent (fully async) that decides when to call tools, reads the results, and continues until it can answer.
- **Switch models and providers from the UI** — pick a provider (OpenAI or Ollama) and a specific model per conversation from a two-step selector; the model list is fetched live from each provider, never hardcoded. Anthropic and Google Gemini are wired and activate when their API keys are added.
- **Connect to the MCP ecosystem** — integrates external Model Context Protocol servers (filesystem, web fetch) alongside its own tools, all through one async agent loop. Tools are curated to keep selection sharp.
- **Search and fetch the web** — `web_search` (DuckDuckGo, no API key) to find pages; the MCP `fetch` server to read a specific URL.
- **Answer from your own documents** — advanced RAG: hybrid search (semantic + keyword), Reciprocal Rank Fusion, cross-encoder reranking, and LLM query expansion, with citations.
- **Remember you** — short-term conversation memory (per thread), long-term memory (Postgres), plus a knowledge-graph memory: conversations are written to an Obsidian vault and graphify builds a queryable graph over them, exposed to the agent through the native `graph_query` tool. Memory is verified by an eval harness.
- **Run deep research** — a dedicated pipeline (Research mode): planner decomposes the question, a human approves/edits the sub-questions, parallel ReAct researchers work in isolated contexts, and a synthesizer merges findings into one cited report.
- **Manage your calendar** — a local SQLite calendar with agent tools (add/list/find/delete), a month-view UI, `.ics` export, and upcoming events injected as reminders each turn.
- **Extend itself, safely** — loadable **skills** (`SKILL.md`, progressive disclosure), **subagents** (`AGENT.md` + tool allowlists, e.g. the built-in data-analyst), and agent-drafted skills/tools that wait in a human approval queue (the Skills tab shows drafts and code for review) before they ever load — a two-tier capability firewall.
- **Analyze your data** — drop CSV/Excel/SQLite files in the Data tab; the data-analyst subagent profiles, cleans, and reports with pandas.
- **Pull new local models from the UI** — Ollama registry or Hugging Face GGUFs (`hf.co/org/repo:quant`) with live download progress; delete from the same list.
- **Enforce policy with hooks** — a deterministic lifecycle layer (context injection each turn, tool-call gates that fail closed, uniform tool logging) that the model cannot bypass.
- **Contain the shell** — the agent's `run_shell` runs in a bubblewrap user-namespace sandbox: filesystem read-only outside `data/` and `/tmp`, no network, isolated PIDs.
- **Drive its own development** — a Claude Code tab opens a repo-scoped coding session over a PTY WebSocket.
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
│     ├─ Built-in tools: shell (sandboxed) · web search ·   │
│     │        RAG · memory · graph_query · calendar ·      │
│     │        skills · spawn_agent · metrics · ideas       │
│     ├─ Hooks: session_start context · pre_tool_use gates  │
│     │        (fail-closed) · post_tool_use logging        │
│     └─ MCP tools (config-driven, curated allowlist)       │
├──────────────────────────────────────────────────────────┤
│  Deep research (Research mode): plan → human approval →   │
│     parallel researchers (Send fan-out) → cited synthesis │
├──────────────────────────────────────────────────────────┤
│  Self-extension (capability firewall):                    │
│     skills/ SKILL.md (progressive disclosure) ·           │
│     agents/ AGENT.md + tool allowlists ·                  │
│     agent drafts → pending queue → human review → live    │
├──────────────────────────────────────────────────────────┤
│  Sandbox (bubblewrap userns): RO filesystem outside       │
│     data/ + /tmp · no network · isolated PIDs             │
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

143 fast, service-free tests live in `tests/` — the ReAct loop (scripted-LLM harness),
every web endpoint behind the auth wall, WS auth gating, the hooks registry, the
sandbox's isolation properties (probed live), skills/toolgate/subagent stores, calendar,
uploads, research plan parsing, and the classics (pricing, config, chunking, RRF, auth).
No Postgres or API keys needed; the same suite runs in CI on every push.

```bash
pip install -e . --group dev   # pytest/ruff
python -m pytest -q
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
| Sandbox | bubblewrap (user namespaces): RO fs, no net, PID isolation for `run_shell` |
| Extensibility | skills (`SKILL.md`) · subagents (`AGENT.md`) · gated agent-written tools (hot-loaded post-review) |
| Observability | Custom metrics → Postgres → built-in `/stats` view + auto-provisioned Grafana dashboard |
| CI | GitHub Actions: pytest + ruff + frontend build on every push/PR |
| Infrastructure | Docker Compose |

---

## Quick start

### Run the whole stack in Docker (one command)

```bash
cp .env.example .env          # fill in ARGUS_USERNAME / PASSWORD_HASH / SESSION_SECRET
docker compose -f docker/docker-compose.yml up --build
# app on http://localhost:8000 (login-gated), Postgres+pgvector, Grafana
```
The `app` image builds the React frontend and bundles the Python runtime (plus
`node`/`uv` for the MCP servers); Postgres auto-creates the `vector` extension on first
boot. After the first RAG ingest, add the FTS index once (the embedding table is created
lazily by pgvector):
```bash
docker exec argus_pg psql -U argus -d argus -c "
ALTER TABLE langchain_pg_embedding ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', document)) STORED;
CREATE INDEX IF NOT EXISTS idx_fts ON langchain_pg_embedding USING GIN (fts);"
```
The in-container `/term` shell stays disabled by default (it would be a shell into the
container). Provider API keys can be set at runtime from the login-gated **API Keys**
dashboard instead of `.env`.

For local (non-container) development, use the manual setup below.

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
> **Non-Docker runs must build the frontend first.** `dist/` is a git-ignored
> build artifact — if it's absent, the server falls back to the legacy single-file
> UI. The Docker image builds it automatically.

### Run
```bash
python -m app.rag.ingest_demo      # ingest a document
python -m app.eval.runner          # run the memory eval harness
python -m app.web.server           # launch chat UI at http://127.0.0.1:8000 (login required)
```
The server binds **127.0.0.1** by default because the built-in Terminal is a real
shell on the host (login-gated). Set `ARGUS_BIND=0.0.0.0` to expose on the LAN —
only with strong credentials.

**Security / trust model.** Command-execution paths, gated by the single-password
login **and** the localhost-only bind:
- **Terminal tab** (`/term`) and **Claude Code tab** (`/claude`) — intentionally
  unrestricted PTYs for *you*. Disabled entirely on a non-local bind unless
  `ARGUS_TERM_ALLOW_REMOTE=1`.
- **`run_shell` agent tool** — LLM-driven, so it runs inside a **bubblewrap
  sandbox**: filesystem read-only outside `data/` and a per-call `/tmp`, no
  network, isolated PIDs, 30s timeout. A destructive-command denylist remains as
  a fast first filter, and a fail-closed `pre_tool_use` hook re-enforces it at
  the graph layer. Without usable bwrap the tool falls back to the old
  guardrail-only mode with a loud warning (`ARGUS_SANDBOX=off` to opt out).
- **Anything the agent writes for itself** (skills = instructions, tools = code)
  is inert until reviewed and approved in the Skills tab — pending drafts are
  never indexed, never imported.

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
- [x] Containerize the app itself (one-command full stack)
- [x] Deep-research mode (plan → human approval → parallel researchers → cited synthesis)
- [x] Local calendar (agent tools + month-view UI + `.ics` export)
- [x] Claude Code tab (repo-scoped coding session over a PTY WebSocket)
- [x] Skills system + agent factory with a human approval firewall (skills, subagents, gated agent-written tools)
- [x] Local model manager (pull Ollama / Hugging Face GGUF models from the UI with progress)
- [x] Hooks: deterministic lifecycle layer (context injection, fail-closed tool gates, uniform logging)
- [x] Data tab: file uploads analyzed by the data-analyst subagent
- [x] Sandboxed `run_shell` (bubblewrap user namespaces)
- [x] CI (GitHub Actions) + core test coverage (143 tests)
- [ ] Notifications + recurring calendar events
- [ ] RAG quality: streaming retrieval + rerank ablation with measured recall@k

---

## About the author

Built from scratch by **Nick Kantiotis** — [@vigoroth](https://github.com/vigoroth).

Argus is a solo, from-the-ground-up exploration of production-shaped agent engineering:
the async LangGraph ReAct loop, deep-research orchestration with human-in-the-loop
approval, a self-extension system behind a capability firewall (skills, subagents,
gated agent-written tools), a hooks lifecycle layer, a bubblewrap-sandboxed shell, a
full advanced-RAG pipeline (hybrid retrieval → RRF → cross-encoder rerank → citations),
three-tier memory (checkpointer · Postgres · graphify knowledge graph), MCP tool
integration, a multi-provider LLM layer with in-UI model pulling, a login-gated
streaming React UI, an eval harness, CI, and end-to-end observability — all wired
together and containerized as one local-first stack. Sole author and contributor.

<a href="https://github.com/vigoroth"><img src="https://img.shields.io/badge/GitHub-@vigoroth-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub @vigoroth" /></a>

---

## License

Released under the **MIT License** — © Nick Kantiotis.