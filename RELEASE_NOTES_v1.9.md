# Argus v1.9.0 — Canonical Second Brain

## Highlights

- `Second Brain/` is the canonical durable memory store.
- Automatic capture is deterministic, secret-aware, and Git-transactional.
- Retrieval uses section-level FTS5 with stage authority and current-file hashes.
- Obsidian edits are watched by the backend; safe edits are adopted and protected
  edits fail closed.
- `/project`, `/ship`, `/harvest`, `/query`, `/review`, `/approve`, and `/evolve`
  have deterministic routing boundaries.
- Ship and harvest use content-addressed, single-use approval proposals.
- The Brain Audit view shows exact diffs, transactions, disclosures, and rejected
  capture reasons.
- Provider-specific remote-context policy, preview, and disclosure purging are
  available.
- Explicit Git bundle backup validates recovery through a temporary clone.

## Migration

1. Back up Postgres and the `Second Brain/` directory.
2. Open `Second Brain/` as an Obsidian vault.
3. Start Argus and check the Brain status panel.
4. Use **Migrate memory** once to import safe legacy Postgres facts into inbox.
5. Review and promote imported material through normal project workflows.

Legacy Postgres memory is not deleted by migration. Graphify, automatic transcript
vault export, and model-controlled memory tools have been removed from runtime.

## Security behavior

- Remote Brain context defaults to the explicitly listed providers.
- Set `ARGUS_BRAIN_REMOTE_CONTEXT=deny` for local-only canonical memory.
- Secret-like captures are rejected without storing their payload in rejection logs.
- Protected output/wiki changes require an exact proposal hash and current base.
- Brain approval never authorizes publishing, pushing, messaging, or other external
  effects.

## Backup and recovery

The authenticated Brain backup operation creates a local Git bundle under
`data/brain_backups/` by default and verifies it by cloning into a temporary
directory. Operational SQLite databases and credentials are not included.

To recover manually:

```bash
git clone data/brain_backups/second-brain-YYYYMMDD-HHMMSS.bundle restored-brain
python restored-brain/.agents/evals/validate_pack.py
```

After restore, point `ARGUS_BRAIN_PATH` at the validated repository and rebuild
the search index from the Brain Audit view.

## Rollback

- Disable capture with `ARGUS_BRAIN_AUTO_CAPTURE=false`.
- Disable context injection with `ARGUS_BRAIN_CONTEXT=false`.
- Disable the watcher with `ARGUS_BRAIN_WATCH=false`.
- Set `ARGUS_BRAIN_REMOTE_CONTEXT=deny` to prevent remote disclosure.
- Canonical note rollback should use a reviewed compensating Git transaction;
  never rewrite or reset Brain history.

## Known release gate

Focused Brain tests, lint, the frontend production build, and the Brain contract
validator pass. On the current Python 3.13 environment, the installed pytest/plugin
stack can remain alive after successful async LangGraph/TestClient assertions.
Standalone graph execution closes correctly. Resolve or pin this teardown
combination before tagging v1.9.0.
