"""Real local terminal over WebSocket: auth-gated PTY running bash.

Security: this hands a real shell on the host to anyone holding a valid Argus
session cookie. The WS handshake re-validates the signed session cookie, and
the server binds 127.0.0.1 by default (see server.main). When ARGUS_BIND is
non-local the endpoint is disabled entirely unless ARGUS_TERM_ALLOW_REMOTE=1
is set explicitly. Treat the login credentials accordingly.
"""
import asyncio
import fcntl
import json
import os
import pty
import shutil
import signal
import struct
import termios
from pathlib import Path

from fastapi import WebSocket

from app.web.auth import COOKIE_NAME, valid_token

# repo root: app/web/term.py -> parents[2] == …/argus
REPO_ROOT = Path(__file__).resolve().parents[2]

# First message seeded into the Claude Code tab: it kicks off the lab upgrade loop.
CLAUDE_BOOTSTRAP = (
    "You're working inside the Argus repo. Read lab/IDEAS.md, pick a 'next' upgrade, "
    "scaffold it with `python lab/lab.py new \"<title>\"`, implement it, add tests, "
    "write the upgrade notes.md, then run `python lab/lab.py sync`. "
    "Ask before each edit or command."
)


def _valid_ws_session(ws: WebSocket) -> bool:
    """Same check as auth.valid_session, against the WS handshake cookies."""
    return valid_token(ws.cookies.get(COOKIE_NAME))


def term_enabled() -> bool:
    """Shell endpoint is localhost-only unless explicitly opted into."""
    bind = os.environ.get("ARGUS_BIND") or os.environ.get("NEXUS_BIND", "127.0.0.1")
    if bind in ("127.0.0.1", "localhost", "::1"):
        return True
    return (os.environ.get("ARGUS_TERM_ALLOW_REMOTE")
            or os.environ.get("NEXUS_TERM_ALLOW_REMOTE")) == "1"


async def _pty_session(ws: WebSocket, argv: list[str], cwd: str) -> None:
    """Bridge a WebSocket to a PTY running `argv` in `cwd`.

    Gating (localhost/auth) is the caller's responsibility. Shared by the bash
    terminal (/term) and the Claude Code tab (/claude) — same primitive, different
    command + working directory.
    """
    if not term_enabled():
        await ws.close(code=4404)  # disabled on non-local bind
        return
    if not _valid_ws_session(ws):
        await ws.close(code=4403)  # policy violation: not authenticated
        return
    await ws.accept()

    pid, fd = pty.fork()
    if pid == 0:  # child: become the process
        os.chdir(cwd)
        os.environ["TERM"] = "xterm-256color"
        os.execvp(argv[0], argv)
        return  # unreachable

    loop = asyncio.get_running_loop()

    def _resize(cols: int, rows: int) -> None:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    def _read(fd_: int) -> bytes:
        return os.read(fd_, 65536)  # blocks in this executor thread; b"" or OSError = shell exited

    async def pty_to_ws():
        while True:
            try:
                data = await loop.run_in_executor(None, _read, fd)
            except OSError:
                break
            if not data:
                break  # EOF: shell exited
            await ws.send_bytes(data)
        try:
            await ws.close()
        except Exception:
            pass

    async def ws_to_pty():
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            text = msg.get("text")
            data = msg.get("bytes")
            if text:
                # control frames are JSON ({"resize":[cols,rows]}); else raw input
                if text.startswith('{"resize"'):
                    try:
                        cols, rows = json.loads(text)["resize"]
                        _resize(int(cols), int(rows))
                        continue
                    except Exception:
                        pass
                os.write(fd, text.encode())
            elif data:
                os.write(fd, data)

    reader = asyncio.create_task(pty_to_ws())
    try:
        await ws_to_pty()
    except Exception:
        pass
    finally:
        reader.cancel()
        try:
            os.kill(pid, signal.SIGHUP)
            os.close(fd)
        except OSError:
            pass


async def terminal_ws(ws: WebSocket) -> None:
    """/term — a login bash shell in the user's home directory."""
    await _pty_session(ws, ["bash", "-l"], os.path.expanduser("~"))


async def claude_ws(ws: WebSocket) -> None:
    """/claude — an interactive Claude Code session scoped to the repo, seeded
    with the lab-upgrade bootstrap. Same shell-equivalent surface as /term, so it
    inherits the identical localhost/auth gate via _pty_session."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        # gate first so we don't leak "claude missing" to unauthenticated callers
        if not term_enabled() or not _valid_ws_session(ws):
            await ws.close(code=4403)
            return
        await ws.accept()
        await ws.send_text(
            "\r\n\x1b[31mclaude CLI not found on PATH.\x1b[0m "
            "Install Claude Code, then reopen this tab.\r\n"
        )
        await ws.close()
        return
    await _pty_session(ws, [claude_bin, CLAUDE_BOOTSTRAP], str(REPO_ROOT))
