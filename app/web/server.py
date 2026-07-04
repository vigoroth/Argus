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
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import build_graph
from app.web.conversations import (
    init_tables, create_conversation, list_conversations,
    add_message, get_messages,
)
from app.web.auth import (
    check_login, make_session_token, valid_session,
    require_auth, COOKIE_NAME, MAX_AGE,
)
from app.web.models_list import list_all_models
from app.core.metrics import init_metrics_table, record_run, get_stats_summary
from app.core.pricing import cost_usd
from app.core.config import get_settings
app = FastAPI(title="Nexus")

LOGIN_HTML = """
<!doctype html><html><head><title>Nexus — Login</title>
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
  <h2>Nexus</h2>
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
    return HTMLResponse(LOGIN_HTML.replace("{error}", "Wrong username or password"), status_code=401)

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
_checkpointer_cm = AsyncSqliteSaver.from_conn_string("data/web_memory.sqlite")
CHECKPOINTER = None
GRAPHS = {}  # model_name -> compiled graph
_graph_lock = asyncio.Lock()  # concurrent builds race inside MCP tool loading


async def get_graph(model: str | None = None, provider: str | None = None,
                    plain: bool = False):
    global CHECKPOINTER
    key = f"{provider or 'default'}:{model or 'default'}:{'plain' if plain else 'agent'}"
    if key in GRAPHS:
        return GRAPHS[key]
    async with _graph_lock:
        if CHECKPOINTER is None:
            CHECKPOINTER = await _checkpointer_cm.__aenter__()
        if key not in GRAPHS:  # re-check under the lock
            GRAPHS[key] = await build_graph(checkpointer=CHECKPOINTER, model=model,
                                            provider=provider, plain=plain)
    return GRAPHS[key]


init_tables()
init_metrics_table()


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    model: str | None = None
    provider: str | None = None
    mode: str = "agent"  # "agent" (tools) | "chat" (plain LLM)


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
    from app.web.vault_writer import graph_build_status
    from app.web.term import term_enabled
    return {"graph": graph_build_status(), "term_enabled": term_enabled()}


@app.get("/conversations", dependencies=[Depends(require_auth)])
def conversations():
    """List all conversations for the sidebar."""
    return list_conversations()


@app.get("/conversations/{conv_id}", dependencies=[Depends(require_auth)])
def conversation_messages(conv_id: str):
    """Return all messages in one conversation, to reload it."""
    return get_messages(conv_id)


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


def _activity_and_usage(node_out: dict) -> tuple[list[dict], int, int]:
    """From one LangGraph node's 'updates' output: build activity SSE events
    (tool calls / tool results) and tally token usage from any AI messages."""
    events: list[dict] = []
    in_tokens = out_tokens = 0
    for msg in node_out.get("messages", []):
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                events.append({"event": "activity", "data": json.dumps(f"calling {tc['name']}")})
        if type(msg).__name__ == "ToolMessage":
            name = getattr(msg, "name", "tool")
            events.append({"event": "activity", "data": json.dumps(f"{name} returned")})
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            in_tokens += usage.get("input_tokens", 0)
            out_tokens += usage.get("output_tokens", 0)
    return events, in_tokens, out_tokens


@app.post("/chat", dependencies=[Depends(require_auth)])
async def chat(req: ChatRequest):
    """Stream the agent's reply; persist both user and assistant messages."""
    # blocking psycopg calls run in the threadpool so they never stall the event loop
    conv_id = req.conversation_id or await asyncio.to_thread(create_conversation, req.message)
    await asyncio.to_thread(add_message, conv_id, "user", req.message)

    async def event_generator():
            yield {"event": "conversation", "data": conv_id}
            full_reply = ""
            # per-run metrics (latency, tokens, cost) → run_metrics table
            t0 = time.perf_counter()
            in_tokens = out_tokens = 0
            run_error = None
            model_name = req.model or get_settings().llm_model
            try:
                graph = await get_graph(req.model, req.provider, plain=(req.mode == "chat"))
                config = {"configurable": {"thread_id": conv_id}}
                async for mode, chunk in graph.astream(
                    {"messages": [HumanMessage(content=req.message)]},
                    stream_mode=["messages", "updates"],
                    config=config,
                ):
                    if mode == "messages":
                        # token streaming (chunk is a (message, meta) tuple)
                        msg, _meta = chunk
                        content = getattr(msg, "content", None)
                        if content and isinstance(content, str):
                            full_reply += content
                            yield {"data": json.dumps(content)}
                    elif mode == "updates":
                        # node-level updates — surface tool activity + tally usage
                        for node_out in chunk.values():
                            events, dt_in, dt_out = _activity_and_usage(node_out)
                            in_tokens += dt_in
                            out_tokens += dt_out
                            for ev in events:
                                yield ev
            except Exception as e:
                run_error = str(e)
                yield {"event": "activity", "data": json.dumps(f"error: {run_error[:120]}")}
            finally:
                # metrics + persisting the reply are independent writes — run them
                # concurrently instead of back-to-back thread hops
                metrics_task = asyncio.create_task(asyncio.to_thread(
                    record_run,
                    "chat", (time.perf_counter() - t0) * 1000,
                    in_tokens, out_tokens,
                    cost_usd(model_name, in_tokens, out_tokens),
                    run_error is None, run_error,
                    conversation_id=conv_id, model=model_name,
                ))
                save_task = asyncio.create_task(
                    asyncio.to_thread(add_message, conv_id, "assistant", full_reply))
                try:
                    await metrics_task  # metrics must never break chat
                except Exception as e:
                    print(f"metrics write skipped: {e}")
                await save_task
            # let the client render the reply now; persistence below is housekeeping
            yield {"event": "done", "data": ""}
            # also write the whole conversation to the Obsidian vault
            try:
                from app.web.vault_writer import write_conversation, refresh_graph
                from app.web.conversations import list_conversations

                def _vault_sync():
                    msgs = get_messages(conv_id)
                    title = next((c["title"] for c in list_conversations()
                                if c["id"] == conv_id), conv_id)
                    write_conversation(conv_id, title, msgs)
                    refresh_graph()   # non-blocking Popen (debounced)
                await asyncio.to_thread(_vault_sync)
            except Exception as e:
                print(f"vault write skipped: {e}")

    return EventSourceResponse(event_generator())


# real local terminal (PTY over WS, auth-gated) — see app/web/term.py
from app.web.term import terminal_ws
app.add_api_websocket_route("/term", terminal_ws)

# hashed asset bundles from the React build (index.html stays auth-gated above)
if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


def main() -> None:
    import uvicorn
    import os
    # default localhost-only: the /term endpoint is a real shell behind the login
    host = os.environ.get("NEXUS_BIND", "127.0.0.1")
    uvicorn.run(app, host=host, port=8000)


if __name__ == "__main__":
    main()