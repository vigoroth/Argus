"""Phase 2: FastAPI backend with conversation persistence + streaming + auth.

Run:  python -m app.web.server
Then open http://localhost:8000
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import asyncio
import json
import time

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import build_graph
from app.agent.research import build_research_graph
from app.core.config import configure_tracing, get_settings
from app.core.logging_config import configure_logging, get_logger
from app.core.metrics import (
    get_activity,
    get_stats_summary,
    init_activity_table,
    init_metrics_table,
    record_activity,
    record_run,
)
from app.core.pricing import cost_usd
from app.memory.long_term import init_memory_table
from app.web.auth import (
    COOKIE_NAME,
    MAX_AGE,
    check_login,
    make_session_token,
    require_auth,
    valid_session,
)
from app.web.conversations import (
    add_message,
    create_conversation,
    get_messages,
    init_tables,
    list_conversations,
)
from app.web.models_list import list_all_models
from app.web.secrets_store import (
    PROVIDERS,
    apply_secrets,
    init_secrets_table,
    secret_status,
    set_secret,
)

configure_logging()
log = get_logger("argus.web.server")
configure_tracing()  # export LangSmith env vars if tracing is enabled in .env
app = FastAPI(title="Argus")

LOGIN_HTML = """
<!doctype html><html><head><title>Argus — Login</title>
<style>
  body{background:#121212;color:#e8e8e8;font-family:system-ui;display:flex;
       align-items:center;justify-content:center;height:100vh;margin:0}
  form{background:#1e1e1e;padding:32px;border-radius:12px;border:1px solid #333}
  h2{margin:0 0 16px;color:#d97757}
  input{display:block;width:240px;padding:10px;margin:8px 0;background:#252525;
        border:1px solid #444;border-radius:6px;color:#fff}
  button{padding:10px 20px;background:#d97757;border:0;border-radius:6px;
         color:#fff;cursor:pointer;font-weight:600}
  .err{color:#e06c6c;font-size:13px;height:16px}
</style></head><body>
<form method="post" action="/login">
  <h2>Argus</h2>
  <input type="text" name="username" placeholder="Username" autofocus>
  <input type="password" name="password" placeholder="Password">
  <div class="err">{error}</div>
  <button type="submit">Enter</button>
</form></body></html>
"""






@app.get("/login")
def login_page():
    return HTMLResponse(LOGIN_HTML.replace("{error}", ""))


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if check_login(username, password):
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(
            COOKIE_NAME, make_session_token(),
            max_age=MAX_AGE, httponly=True, samesite="lax",
        )
        return resp
    return HTMLResponse(
        LOGIN_HTML.replace("{error}", "Wrong username or password"), status_code=401
    )

@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp



@app.get("/models", dependencies=[Depends(require_auth)])
async def models():
    """Return available models grouped by provider, for the selector."""
    return await list_all_models()


# persistent async checkpointer for per-conversation memory (built lazily)
Path("data").mkdir(exist_ok=True)  # sqlite checkpointer dir (gitignored, absent on fresh clones)
_checkpointer_cm = AsyncSqliteSaver.from_conn_string("data/web_memory.sqlite")
CHECKPOINTER = None
GRAPHS = {}  # model_name -> compiled graph
_graph_lock = asyncio.Lock()  # concurrent builds race inside MCP tool loading


async def get_graph(model: str | None = None, provider: str | None = None,
                    mode: str = "agent"):
    """Compiled graph for a (provider, model, mode) triple, cached. Modes:
    'agent' (ReAct + tools), 'chat' (plain LLM), 'research' (deep-research orchestrator)."""
    global CHECKPOINTER
    key = f"{provider or 'default'}:{model or 'default'}:{mode}"
    if key in GRAPHS:
        return GRAPHS[key]
    async with _graph_lock:
        if CHECKPOINTER is None:
            CHECKPOINTER = await _checkpointer_cm.__aenter__()
        if key not in GRAPHS:  # re-check under the lock
            if mode == "research":
                GRAPHS[key] = await build_research_graph(
                    checkpointer=CHECKPOINTER, model=model, provider=provider)
            else:
                GRAPHS[key] = await build_graph(
                    checkpointer=CHECKPOINTER, model=model, provider=provider,
                    plain=(mode == "chat"))
    return GRAPHS[key]


init_tables()
init_metrics_table()
init_activity_table()
init_memory_table()
init_secrets_table()
from app.calendar.store import init_calendar_table

init_calendar_table()
apply_secrets(GRAPHS)  # load any dashboard-set keys into env + Settings at boot


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    model: str | None = None
    provider: str | None = None
    mode: str = "agent"  # "agent" (tools) | "chat" (plain LLM) | "research" (deep research)


class SecretRequest(BaseModel):
    provider: str
    key: str


FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"


@app.get("/")
def index(request: Request):
    if not valid_session(request):
        return RedirectResponse(url="/login", status_code=303)
    # prefer the built React app; fall back to the legacy single-file UI
    built = FRONTEND_DIST / "index.html"
    html = built if built.exists() else Path(__file__).parent / "index.html"
    return HTMLResponse(html.read_text(encoding="utf-8"),
                        headers={"Cache-Control": "no-store"})


@app.get("/status", dependencies=[Depends(require_auth)])
def status():
    """Lightweight status for the sidebar dot (graph build state)."""
    from app.web.term import term_enabled
    from app.web.vault_writer import graph_build_status
    return {"graph": graph_build_status(), "term_enabled": term_enabled()}


@app.get("/conversations", dependencies=[Depends(require_auth)])
def conversations():
    """List all conversations for the sidebar."""
    return list_conversations()


@app.get("/conversations/{conv_id}", dependencies=[Depends(require_auth)])
def conversation_messages(conv_id: str):
    """Return all messages in one conversation, to reload it."""
    return get_messages(conv_id)


@app.get("/conversations/{conv_id}/activity", dependencies=[Depends(require_auth)])
def conversation_activity(conv_id: str):
    """Return the persisted activity log (tool calls / results) for a conversation."""
    return get_activity(conv_id)


@app.get("/secrets", dependencies=[Depends(require_auth)])
def secrets_status():
    """Which providers have a key set (write-only — values never leave the server)."""
    return secret_status()


@app.post("/secrets", dependencies=[Depends(require_auth)])
def secrets_set(req: SecretRequest):
    """Encrypt + store one provider key, then apply it live (env + Settings + graph cache)."""
    if req.provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail="unknown provider")
    if not req.key.strip():
        raise HTTPException(status_code=400, detail="empty key")
    set_secret(req.provider, req.key.strip())
    apply_secrets(GRAPHS)
    return {"ok": True}


@app.get("/graph", dependencies=[Depends(require_auth)])
def knowledge_graph():
    """Serve the graphify knowledge graph (networkx node-link JSON) over the
    Obsidian vault, for the 3D graph view. Cached by mtime and capped to the
    largest communities — see app.tools.graph_query.get_graph_data."""
    from app.tools.graph_query import get_graph_data
    return get_graph_data()


@app.get("/stats", dependencies=[Depends(require_auth)])
def stats():
    """Aggregate run metrics for the Stats dashboard: lifetime totals,
    a 14-day daily series, and the last 20 runs. Empty-table safe."""
    return get_stats_summary()


@app.get("/calendar.ics", dependencies=[Depends(require_auth)])
def calendar_ics():
    """Export the local calendar as iCalendar, so it can be subscribed to from any
    calendar app (the agent manages events; this is the read-only feed)."""
    from fastapi.responses import Response

    from app.calendar.store import export_ics
    return Response(export_ics(), media_type="text/calendar")


@app.get("/calendar", dependencies=[Depends(require_auth)])
def calendar_list():
    """All calendar events (chronological) for the Calendar view."""
    from app.calendar.store import list_events
    return list_events(start="0001-01-01T00:00")


class EventRequest(BaseModel):
    title: str
    start: str
    end: str | None = None
    location: str | None = None
    notes: str | None = None


@app.post("/calendar", dependencies=[Depends(require_auth)])
def calendar_create(req: EventRequest):
    """Create an event from the Calendar view (ISO 8601 datetimes)."""
    from app.calendar.store import add_event
    try:
        eid = add_event(req.title, req.start, req.end, req.location, req.notes)
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be ISO 8601") from None
    return {"id": eid}


@app.delete("/calendar/{event_id}", dependencies=[Depends(require_auth)])
def calendar_delete(event_id: int):
    """Delete one event by id from the Calendar view."""
    from app.calendar.store import delete_event
    return {"ok": delete_event(event_id)}


# ── skills (Upgrade 004): live index + human approval queue for agent drafts ──

@app.get("/skills", dependencies=[Depends(require_auth)])
def skills_list():
    """Live skills, pending skill drafts, subagents, and pending tool code —
    everything the Skills tab reviews."""
    from app.skills.loader import list_pending, list_skills
    from app.skills.toolgate import list_pending_tools
    from app.subagents.loader import list_agents
    live = [{"name": s["name"], "description": s["description"]} for s in list_skills()]
    pending = [{"name": s["name"], "description": s["description"], "body": s["body"]}
               for s in list_pending()]
    agents = [{"name": a["name"], "description": a["description"],
               "tools": a["tools"]} for a in list_agents()]
    return {"live": live, "pending": pending, "agents": agents,
            "pending_tools": list_pending_tools()}


@app.post("/skills/{name}/approve", dependencies=[Depends(require_auth)])
def skills_approve(name: str):
    """Promote a pending agent-drafted skill to live (the capability firewall)."""
    from app.skills.loader import approve_skill
    if not approve_skill(name):
        raise HTTPException(status_code=404, detail="no such pending skill")
    return {"ok": True}


@app.post("/skills/{name}/reject", dependencies=[Depends(require_auth)])
def skills_reject(name: str):
    """Discard a pending agent-drafted skill."""
    from app.skills.loader import reject_skill
    if not reject_skill(name):
        raise HTTPException(status_code=404, detail="no such pending skill")
    return {"ok": True}


@app.post("/tools/{name}/approve", dependencies=[Depends(require_auth)])
def tools_approve(name: str):
    """Promote a pending agent-written TOOL (code) to live after human review.
    Clears the graph cache so the next request rebuilds with the new tool bound."""
    from app.skills.toolgate import approve_tool
    if not approve_tool(name):
        raise HTTPException(status_code=404, detail="no such pending tool")
    GRAPHS.clear()  # hot-load: next get_graph() re-runs build_graph -> load_custom_tools
    return {"ok": True}


@app.post("/tools/{name}/reject", dependencies=[Depends(require_auth)])
def tools_reject(name: str):
    """Discard a pending agent-written tool draft."""
    from app.skills.toolgate import reject_tool
    if not reject_tool(name):
        raise HTTPException(status_code=404, detail="no such pending tool")
    return {"ok": True}


def _snippet(value, limit: int = 80) -> str:
    """Compact one-line preview of tool args or a tool result."""
    s = " ".join(str(value).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _activity_and_usage(node_out: dict) -> tuple[list[dict], int, int]:
    """From one LangGraph node's 'updates' output: build structured activity
    entries ({'kind','text'} — tool calls / results) and tally token usage."""
    events: list[dict] = []
    in_tokens = out_tokens = 0
    # a no-op node (e.g. summarize below its trigger) streams a None/empty update
    if not node_out:
        return events, in_tokens, out_tokens
    for msg in node_out.get("messages", []):
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                args = tc.get("args") or {}
                arg_str = _snippet(args) if args else ""
                text = f"→ {tc['name']}({arg_str})" if arg_str else f"→ {tc['name']}"
                events.append({"kind": "tool_call", "text": text})
        if type(msg).__name__ == "ToolMessage":
            name = getattr(msg, "name", "tool")
            result = _snippet(getattr(msg, "content", ""))
            text = f"← {name}: {result}" if result else f"← {name} returned"
            events.append({"kind": "tool_result", "text": text})
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            in_tokens += usage.get("input_tokens", 0)
            out_tokens += usage.get("output_tokens", 0)
    return events, in_tokens, out_tokens


async def _stream_run(graph, graph_input, conv_id: str, model_name: str, label: str):
    """Shared SSE generator for a single graph run. Used by /chat (fresh turn) and
    /chat/resume (continuing a paused research run — graph_input is a Command there).
    Streams tokens + activity, emits a `plan` event if the graph pauses at an
    interrupt, then persists the reply + metrics + vault note (only if a reply was
    produced — the research planning phase intentionally yields no assistant text)."""
    yield {"event": "conversation", "data": conv_id}
    full_reply = ""
    activity_log: list[dict] = []
    t0 = time.perf_counter()
    in_tokens = out_tokens = 0
    run_error = None
    config = {"configurable": {"thread_id": conv_id}}
    try:
        async for mode, chunk in graph.astream(
            graph_input, stream_mode=["messages", "updates"], config=config,
        ):
            if mode == "messages":
                msg, _meta = chunk
                content = getattr(msg, "content", None)
                if content and isinstance(content, str):
                    full_reply += content
                    yield {"data": json.dumps(content)}
            elif mode == "updates":
                # research plan-approval gate: the graph paused for the human
                if "__interrupt__" in chunk:
                    plan = chunk["__interrupt__"][0].value.get("plan", [])
                    yield {"event": "plan", "data": json.dumps(plan)}
                    continue
                for node_out in chunk.values():
                    events, dt_in, dt_out = _activity_and_usage(node_out)
                    in_tokens += dt_in
                    out_tokens += dt_out
                    for ev in events:
                        activity_log.append(ev)
                        yield {"event": "activity", "data": json.dumps(ev)}
    except Exception as e:
        run_error = str(e)
        err_ev = {"kind": "error", "text": f"error: {run_error[:120]}"}
        activity_log.append(err_ev)
        yield {"event": "activity", "data": json.dumps(err_ev)}
    finally:
        metrics_task = asyncio.create_task(asyncio.to_thread(
            record_run,
            label, (time.perf_counter() - t0) * 1000,
            in_tokens, out_tokens,
            cost_usd(model_name, in_tokens, out_tokens),
            run_error is None, run_error,
            conversation_id=conv_id, model=model_name,
        ))
        activity_task = asyncio.create_task(
            asyncio.to_thread(record_activity, conv_id, activity_log))
        # only persist an assistant message when there actually is a reply
        save_task = (asyncio.create_task(
            asyncio.to_thread(add_message, conv_id, "assistant", full_reply))
            if full_reply else None)
        try:
            await metrics_task  # metrics must never break chat
        except Exception as e:
            log.warning("metrics write skipped: %s", e)
        try:
            await activity_task  # activity log must never break chat
        except Exception as e:
            log.warning("activity write skipped: %s", e)
        if save_task:
            await save_task
    yield {"event": "done", "data": ""}
    if not full_reply:
        return  # paused at the plan gate — nothing to sync to the vault yet
    try:
        from app.web.conversations import list_conversations
        from app.web.vault_writer import refresh_graph, write_conversation

        def _vault_sync():
            msgs = get_messages(conv_id)
            title = next((c["title"] for c in list_conversations()
                        if c["id"] == conv_id), conv_id)
            write_conversation(conv_id, title, msgs)
            refresh_graph()   # non-blocking Popen (debounced)
        await asyncio.to_thread(_vault_sync)
    except Exception as e:
        log.warning("vault write skipped: %s", e)


@app.post("/chat", dependencies=[Depends(require_auth)])
async def chat(req: ChatRequest):
    """Stream the agent's reply; persist both user and assistant messages.
    Research mode runs plan → pauses at the approval gate (emits a `plan` event);
    the client approves via /chat/resume."""
    conv_id = req.conversation_id or await asyncio.to_thread(create_conversation, req.message)
    await asyncio.to_thread(add_message, conv_id, "user", req.message)
    model_name = req.model or get_settings().llm_model
    graph = await get_graph(req.model, req.provider, mode=req.mode)
    graph_input = ({"question": req.message} if req.mode == "research"
                   else {"messages": [HumanMessage(content=req.message)]})
    return EventSourceResponse(
        _stream_run(graph, graph_input, conv_id, model_name, req.mode))


class ResumeRequest(BaseModel):
    conversation_id: str
    plan: list[str]
    model: str | None = None
    provider: str | None = None


@app.post("/chat/resume", dependencies=[Depends(require_auth)])
async def chat_resume(req: ResumeRequest):
    """Resume a paused deep-research run with the (possibly edited) approved plan.
    Runs the parallel researchers + synthesis and streams the cited report."""
    from langgraph.types import Command
    model_name = req.model or get_settings().llm_model
    graph = await get_graph(req.model, req.provider, mode="research")
    return EventSourceResponse(
        _stream_run(graph, Command(resume=req.plan),
                    req.conversation_id, model_name, "research"))


# real local terminal (PTY over WS, auth-gated) — see app/web/term.py
from app.web.term import claude_ws, terminal_ws

app.add_api_websocket_route("/term", terminal_ws)
app.add_api_websocket_route("/claude", claude_ws)  # Claude Code session in the repo

# hashed asset bundles from the React build (index.html stays auth-gated above)
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


def _port_holder(host: str, port: int) -> int | None:
    """PID of the process LISTENing on host:port, or None if the port is free.

    Stdlib-only (no psutil): parse `ss`, fall back to `lsof`. Returns the first
    matching listener; None when nothing holds the port or neither tool exists.
    """
    import re
    import shutil
    import subprocess

    if shutil.which("ss"):
        out = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            local = line.split()[3:4]  # Local Address:Port column
            if not local or not local[0].endswith(f":{port}"):
                continue
            m = re.search(r"pid=(\d+)", line)
            if m:
                return int(m.group(1))
    if shutil.which("lsof"):
        out = subprocess.run(
            ["lsof", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True,
        ).stdout.strip()
        if out:
            return int(out.splitlines()[0])
    return None


def _cmdline(pid: int) -> str:
    """Best-effort process command line for a PID (empty string if unreadable)."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\x00", b" ").decode(errors="replace").strip()
    except OSError:
        import subprocess
        return subprocess.run(
            ["ps", "-o", "cmd=", "-p", str(pid)], capture_output=True, text=True,
        ).stdout.strip()


def _free_port(host: str, port: int) -> None:
    """Ensure host:port is bindable before uvicorn starts.

    If a *stale instance of this same server* holds it, terminate that process
    and wait for the socket to free. If a foreign process holds it, exit cleanly
    with guidance instead of letting uvicorn raise a raw EADDRINUSE traceback.
    """
    import os
    import signal
    import time

    pid = _port_holder(host, port)
    if pid is None or pid == os.getpid():
        return

    cmd = _cmdline(pid)
    if "app.web.server" not in cmd:
        log.error("port %s is held by PID %s (%s).", port, pid, cmd or "unknown process")
        log.error("stop it, or start on another port:  ARGUS_PORT=<n> python -m app.web.server")
        raise SystemExit(1)

    log.info("port %s held by stale PID %s (our server) — terminating…", port, pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return  # already gone between check and kill

    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        time.sleep(0.25)
        if _port_holder(host, port) is None:
            log.info("stale PID %s stopped — port %s free.", pid, port)
            return
    # SIGTERM ignored within the grace window — force it
    log.warning("stale PID %s ignored SIGTERM — sending SIGKILL.", pid)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    time.sleep(0.5)


def main() -> None:
    import os

    import uvicorn
    # default localhost-only: the /term endpoint is a real shell behind the login
    host = os.environ.get("ARGUS_BIND") or os.environ.get("NEXUS_BIND", "127.0.0.1")
    port = int(os.environ.get("ARGUS_PORT", "8000"))
    _free_port(host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()