"""Content-addressed proposal and approval ledger for protected Brain changes."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

from app.brain import service
from app.brain.service import BrainError

PROTECTED_OPERATIONS = {"delete", "destructive-merge", "ship", "harvest", "evolve"}
STATES = {"pending", "approved", "executed", "rejected", "expired"}


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(payload: dict) -> str:
    return "sha256:" + hashlib.sha256(_canonical(payload).encode()).hexdigest()


def _connect() -> sqlite3.Connection:
    conn = service._db()  # operational projection; canonical result remains Git
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS brain_proposals (
          proposal_id TEXT PRIMARY KEY, operation TEXT NOT NULL,
          state TEXT NOT NULL, goal_id TEXT NOT NULL, base_commit TEXT NOT NULL,
          diff_hash TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
          expires_on TEXT NOT NULL, approved_at TEXT, executed_at TEXT,
          receipt TEXT, rejection_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS brain_approvals (
          id INTEGER PRIMARY KEY AUTOINCREMENT, proposal_id TEXT NOT NULL,
          diff_hash TEXT NOT NULL, approved_at TEXT NOT NULL,
          consumed_at TEXT, UNIQUE(proposal_id, diff_hash)
        );
        CREATE TABLE IF NOT EXISTS brain_rejections (
          id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
          source TEXT NOT NULL, reason TEXT NOT NULL
        );
        """
    )
    return conn


def _safe_rel(rel: str) -> str:
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts or len(path.parts) != 2:
        raise BrainError(f"invalid proposal path: {rel}")
    if path.parts[0] not in service.STAGES or path.suffix != ".md":
        raise BrainError(f"path is outside knowledge stages: {rel}")
    return path.as_posix()


def _path_binding(operation: str, paths: list[str], deletions: list[str]) -> None:
    for rel in paths:
        stage = Path(rel).parts[0]
        if stage == "wiki" and operation != "harvest":
            raise BrainError("wiki paths require a harvest proposal")
        if stage == "output" and operation not in {"ship", "harvest"}:
            raise BrainError("output paths require ship or harvest")
    for rel in deletions:
        stage = Path(rel).parts[0]
        if stage not in {"inbox", "projects"}:
            raise BrainError("only inbox or project notes may be deleted")
        if operation == "harvest" and stage != "projects":
            raise BrainError("harvest may delete only its finished project")


def _target_hash(rel: str) -> str | None:
    path = service.brain_root() / rel
    return service._sha(path.read_text(encoding="utf-8")) if path.exists() else None


def _patch(changes: dict[str, str | None]) -> str:
    chunks: list[str] = []
    root = service.brain_root()
    for rel in sorted(changes):
        path = root / rel
        old = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
        new_value = changes[rel]
        new = new_value.splitlines(keepends=True) if new_value is not None else []
        chunks.extend(
            difflib.unified_diff(old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}")
        )
    return "".join(chunks)


def create_proposal(
    operation: str,
    changes: dict[str, str | None],
    *,
    goal_id: str,
    provenance: list[dict] | None = None,
    index_changes: list[dict] | None = None,
    external_effects: list[dict] | None = None,
    expires_on: str | None = None,
) -> dict:
    if operation not in PROTECTED_OPERATIONS:
        raise BrainError(f"unsupported protected operation: {operation}")
    changes = {
        rel: body
        for rel, body in changes.items()
        if (
            body is None
            and (service.brain_root() / rel).exists()
            or body is not None
            and (
                not (service.brain_root() / rel).exists()
                or (service.brain_root() / rel).read_text(encoding="utf-8") != body
            )
        )
    }
    if not changes:
        raise BrainError("proposal has no changes")
    paths = [_safe_rel(rel) for rel in sorted(changes)]
    deletions = [rel for rel, body in changes.items() if body is None]
    _path_binding(operation, paths, deletions)
    if service._status_paths():
        raise BrainError("brain must be clean before creating a proposal")
    proposal_id = (
        f"proposal-{date.today().isoformat()}-{operation}-{uuid.uuid4().hex[:8]}"
    )
    payload = {
        "schema_version": "change-proposal.v1",
        "proposal_id": proposal_id,
        "operation": operation,
        "goal_id": goal_id,
        "base_commit": service._head(),
        "target_hashes": {rel: _target_hash(rel) for rel in paths},
        "paths": paths,
        "patch": _patch(changes),
        "provenance": provenance or [],
        "index_changes": index_changes or [],
        "deletions": sorted(deletions),
        "external_effects": external_effects or [],
        "created_on": date.today().isoformat(),
        "expires_on": expires_on or date.today().isoformat(),
        "changes": changes,
    }
    hash_payload = {k: v for k, v in payload.items() if k not in {"changes"}}
    payload["diff_hash"] = _digest(hash_payload)
    now = datetime.now().astimezone().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO brain_proposals("
            "proposal_id,operation,state,goal_id,base_commit,diff_hash,payload,"
            "created_at,expires_on) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                proposal_id,
                operation,
                "pending",
                goal_id,
                payload["base_commit"],
                payload["diff_hash"],
                _canonical(payload),
                now,
                payload["expires_on"],
            ),
        )
    return payload


def list_proposals(state: str | None = None) -> list[dict]:
    if state and state not in STATES:
        raise BrainError("invalid proposal state")
    query = "SELECT * FROM brain_proposals"
    args: tuple = ()
    if state:
        query += " WHERE state=?"
        args = (state,)
    query += " ORDER BY created_at DESC"
    with _connect() as conn:
        rows = conn.execute(query, args).fetchall()
    return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]


def get_proposal(proposal_id: str) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM brain_proposals WHERE proposal_id=?", (proposal_id,)
        ).fetchone()
    if not row:
        raise BrainError("proposal not found")
    return {**dict(row), "payload": json.loads(row["payload"])}


def approve_proposal(proposal_id: str, diff_hash: str) -> dict:
    proposal = get_proposal(proposal_id)
    if proposal["state"] != "pending":
        raise BrainError(f"proposal is {proposal['state']}")
    if proposal["diff_hash"] != diff_hash:
        raise BrainError("approval hash does not match proposal")
    if proposal["expires_on"] < date.today().isoformat():
        with _connect() as conn:
            conn.execute(
                "UPDATE brain_proposals SET state='expired' WHERE proposal_id=?",
                (proposal_id,),
            )
        raise BrainError("proposal expired")
    payload = proposal["payload"]
    if service._head() != payload["base_commit"]:
        raise BrainError("proposal base commit changed")
    for rel, expected in payload["target_hashes"].items():
        if _target_hash(rel) != expected:
            raise BrainError(f"proposal target changed: {rel}")
    now = datetime.now().astimezone().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO brain_approvals(proposal_id,diff_hash,approved_at) "
            "VALUES(?,?,?)",
            (proposal_id, diff_hash, now),
        )
        conn.execute(
            "UPDATE brain_proposals SET state='approved',approved_at=? "
            "WHERE proposal_id=?",
            (now, proposal_id),
        )
    return get_proposal(proposal_id)


def execute_proposal(proposal_id: str) -> dict:
    with service._LOCK:
        proposal = get_proposal(proposal_id)
        if proposal["state"] != "approved":
            raise BrainError("proposal requires exact approval")
        payload = proposal["payload"]
        if service._head() != payload["base_commit"] or service._status_paths():
            raise BrainError("brain base or worktree changed after approval")
        for rel, expected in payload["target_hashes"].items():
            if _target_hash(rel) != expected:
                raise BrainError(f"approved target changed: {rel}")
        for rel, body in payload["changes"].items():
            path = service.brain_root() / rel
            if body is None:
                path.unlink()
            else:
                path.write_text(body, encoding="utf-8")
        receipt = service._commit(
            payload["paths"], payload["operation"], proposal_id
        )
        now = datetime.now().astimezone().isoformat()
        with _connect() as conn:
            conn.execute(
                "UPDATE brain_approvals SET consumed_at=? "
                "WHERE proposal_id=? AND diff_hash=?",
                (now, proposal_id, proposal["diff_hash"]),
            )
            conn.execute(
                "UPDATE brain_proposals SET state='executed',executed_at=?,receipt=? "
                "WHERE proposal_id=?",
                (now, _canonical(receipt), proposal_id),
            )
        return receipt


def reject_proposal(proposal_id: str, reason: str) -> dict:
    proposal = get_proposal(proposal_id)
    if proposal["state"] not in {"pending", "approved"}:
        raise BrainError(f"proposal is {proposal['state']}")
    with _connect() as conn:
        conn.execute(
            "UPDATE brain_proposals SET state='rejected',rejection_reason=? "
            "WHERE proposal_id=?",
            (reason[:500], proposal_id),
        )
    return get_proposal(proposal_id)


def record_rejection(source: str, reason: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO brain_rejections(ts,source,reason) VALUES(?,?,?)",
            (datetime.now().astimezone().isoformat(), source, reason[:500]),
        )


def list_audit(limit: int = 100) -> dict:
    with _connect() as conn:
        disclosures = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM brain_disclosures ORDER BY id DESC LIMIT ?", (limit,)
            )
        ]
        rejections = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM brain_rejections ORDER BY id DESC LIMIT ?", (limit,)
            )
        ]
    log_lines = service._git(
        "log", f"-{min(limit, 100)}", "--format=%H%x09%aI%x09%s", check=False
    ).splitlines()
    transactions = [
        {"commit": p[0], "timestamp": p[1], "subject": p[2]}
        for line in log_lines
        if len(p := line.split("\t", 2)) == 3
    ]
    return {
        "transactions": transactions,
        "proposals": list_proposals()[:limit],
        "disclosures": disclosures,
        "rejections": rejections,
    }


def parse_approval_command(command: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"/approve\s+(\S+)\s+(sha256:[0-9a-f]{64})\s*", command)
    return (match.group(1), match.group(2)) if match else None
