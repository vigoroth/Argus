"""Knowledge-graph query tool — queries the graphify graph built over the
Obsidian vault (past conversations + notes).

The vault is written by app.web.vault_writer and indexed by graphify into
<vault>/graphify-out/graph.json. `graphify query` does a BFS traversal of that
graph (no LLM needed), returning the relevant nodes and edges as context.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from app.core.config import get_settings

VAULT_PATH = Path(get_settings().nexus_vault_path)
GRAPH_JSON = VAULT_PATH / "graphify-out" / "graph.json"

# cache the parsed graph.json by mtime — /graph and graph_query hit this often
# and the file only changes when a graphify extract/update finishes
_graph_cache: tuple[float, dict] | None = None
MAX_GRAPH_NODES = 1500  # past this, the 3D view chugs — keep the largest communities


def get_graph_data() -> dict:
    """Read graph.json (cached by mtime), capped to the largest communities
    if it's grown past MAX_GRAPH_NODES. Single source of truth for /graph."""
    global _graph_cache
    if not GRAPH_JSON.exists():
        return {"nodes": [], "links": []}
    mtime = GRAPH_JSON.stat().st_mtime
    if _graph_cache and _graph_cache[0] == mtime:
        return _graph_cache[1]

    try:
        raw = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"graph read failed: {e}")
        return {"nodes": [], "links": []}
    nodes, links = raw.get("nodes", []), raw.get("links", [])

    if len(nodes) > MAX_GRAPH_NODES:
        sizes: dict = {}
        for n in nodes:
            sizes[n.get("community")] = sizes.get(n.get("community"), 0) + 1
        kept, count = set(), 0
        for community, size in sorted(sizes.items(), key=lambda kv: -kv[1]):
            if count + size > MAX_GRAPH_NODES:
                break
            kept.add(community)
            count += size
        ids = {n["id"] for n in nodes if n.get("community") in kept}
        nodes = [n for n in nodes if n["id"] in ids]
        links = [l for l in links if l.get("source") in ids and l.get("target") in ids]

    data = {"nodes": nodes, "links": links}
    _graph_cache = (mtime, data)
    return data

# graphify query stdout lines look like:
#   NODE Nexus [src=Nexus.md loc=None community=12]
#   EDGE Nexus --references [EXTRACTED]--> RAG
_NODE_RE = re.compile(r"^NODE\s+(?P<name>.+?)\s+\[src=(?P<src>.*?)\s+loc=")
_EDGE_RE = re.compile(r"^EDGE\s+(?P<a>.+?)\s+--(?P<rel>.+?)\s+\[.*?\]-->\s+(?P<b>.+?)\s*$")


def _summarize(raw: str, question: str) -> str:
    """Turn graphify's NODE/EDGE traversal dump into a compact readable summary."""
    concepts: dict[str, str] = {}   # name -> source note
    relations: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        m = _NODE_RE.match(line)
        if m:
            src = m.group("src").strip()
            concepts.setdefault(m.group("name").strip(), src)
            continue
        m = _EDGE_RE.match(line)
        if m:
            rel = m.group("rel").strip().replace("_", " ")
            relations.append(f"{m.group('a').strip()} {rel} {m.group('b').strip()}")

    if not concepts and not relations:
        return raw.strip() or "No related context found in the knowledge graph."

    out = [f'Knowledge graph — related context for "{question}":', ""]
    if concepts:
        out.append("Concepts:")
        for name, src in concepts.items():
            out.append(f"- {name}" + (f" (from {src})" if src and src != "None" else ""))
    if relations:
        out.append("")
        out.append("Relationships:")
        out.extend(f"- {r}" for r in relations)
    return "\n".join(out)


@tool
def graph_query(question: str) -> str:
    """Query the knowledge graph of the user's past conversations and vault notes.
    Use this to recall what was discussed in earlier conversations, how topics
    connect, or context the user has built up over time. Returns related concepts
    and the links between them from the graph.
    Do NOT use this for ingested documents (use search_documents) or the live web
    (use web_search).
    """
    graphify = shutil.which("graphify")
    if not graphify:
        return "ERROR: knowledge graph unavailable (graphify not installed)."
    if not GRAPH_JSON.exists():
        return "The knowledge graph is empty — no conversations have been indexed yet."
    try:
        proc = subprocess.run(
            [graphify, "query", question, "--graph", str(GRAPH_JSON), "--budget", "1500"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return "ERROR: knowledge graph query timed out."
    except Exception as e:
        return f"ERROR: knowledge graph query failed: {e}"

    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        return f"ERROR: knowledge graph query failed: {(proc.stderr or out)[:300]}"
    if not out:
        return "No related context found in the knowledge graph."
    return _summarize(out, question)
