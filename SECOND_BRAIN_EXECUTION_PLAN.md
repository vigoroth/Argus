# Argus Second Brain — Ten-Workstream Execution Plan

Date: 2026-07-16
Target: v1.9.0
Status: In progress

## Objective

Finish the Second Brain integration as Argus's canonical, auditable memory
system. Committed Markdown remains authoritative; indexes, caches, watchers, and
operational ledgers remain rebuildable support systems. Protected knowledge
transitions require deterministic validation and explicit approval.

## Global invariants

1. `Second Brain/` is a nested Git repository and the canonical durable store.
2. Every canonical mutation produces an exact-path Git transaction receipt.
3. The model may propose changes but cannot approve protected changes.
4. Questions, code blocks, and secret-like material are not automatically captured.
5. Retrieved notes are re-read from disk and hashed before context injection.
6. Remote disclosure is policy-controlled and locally auditable.
7. Obsidian edits may be adopted automatically only when the vault contracts
   classify them as safe.
8. Existing user work in the Argus worktree is preserved.
9. No parent-repository commit or push is performed without explicit instruction.
10. Each workstream needs focused tests plus the strongest available full-suite check.

## Dependency map

```text
1 Test stability
  └─ 2 Approval ledger
      └─ 3 Lifecycle transitions
          ├─ 4 Obsidian watcher
          ├─ 5 Audit dashboard
          ├─ 6 Retrieval quality
          ├─ 7 Legacy retirement
          ├─ 8 Security controls
          └─ 9 Backup/recovery
              └─ 10 Release preparation
```

## 1. Stabilize test teardown

### Deliverables

- Identify the task or executor preventing `asyncio.run()` from closing.
- Remove import-time or lifecycle background work from graph tests.
- Ensure LangGraph test invocations release resources deterministically.
- Run focused graph/web tests without external timeout wrappers.
- Record any Python-version-specific limitation if it cannot be fixed locally.

### Acceptance checks

- `tests/test_graph_loop.py` exits normally.
- `tests/test_web_endpoints.py` exits normally.
- Full `python -m pytest -q` finishes or produces a precise, isolated failure.
- Ruff and frontend checks remain green.

### Rollback

Revert only the teardown/lifecycle changes; no canonical Brain data is affected.

## 2. Add proposal and approval lifecycle

### Deliverables

- SQLite tables for proposals, approvals, receipts, and rollback references.
- Proposal states: `pending`, `approved`, `executed`, `rejected`, `expired`.
- Content-addressed proposal payloads so approvals bind to exact changes.
- API operations for creating, listing, inspecting, approving, rejecting, and
  executing proposals.
- Deterministic command routing for `/project`, `/review`, `/ship`, `/harvest`,
  `/approve`, and `/evolve`.
- Protected stages and control-plane files require approved proposals.

### Acceptance checks

- A changed proposal invalidates its old approval.
- The actor proposing a protected change cannot implicitly approve it.
- Executed proposals store the Brain commit and exact paths.
- Replays are idempotent or fail safely.

### Rollback

Proposal execution creates compensating rollback proposals; ledger rows are
append-only except for state transitions.

## 3. Complete lifecycle transitions

### Deliverables

- Promote inbox notes into active projects with backlinks and provenance.
- Review project completeness against explicit success checks.
- Ship projects into date-prefixed output notes.
- Harvest supported knowledge into wiki notes without deleting contradictions.
- Mark project lifecycle states and regenerate all affected indexes.
- Add compensating Git transactions for reversible knowledge mutations.

### Acceptance checks

- Invalid filenames, missing evidence, broken links, and illegal state changes fail.
- Shipping and harvesting require approved, content-addressed proposals.
- Every promoted or derived note identifies its sources.
- Lifecycle contract validator continues to pass.

### Rollback

Generate a proposal restoring prior blobs and lifecycle metadata from the parent
transaction.

## 4. Harden Obsidian synchronization

### Deliverables

- Backend watcher with polling fallback and debounce.
- Safe inbox/active-project edits auto-adopted.
- Protected edits, deletes, renames, and conflicts converted into proposals.
- Watcher status, last event, and last error exposed through the Brain API.
- UI polling removed once backend ownership is active.

### Acceptance checks

- Multiple rapid writes produce one adoption transaction.
- Concurrent Argus/Obsidian changes fail closed.
- Status endpoints remain read-only.
- Watcher shutdown does not leak tasks or block tests.

### Rollback

Disable watcher through configuration; manual `/brain/adopt` remains available.

## 5. Build the Brain audit dashboard

### Deliverables

- Transaction history with operation, paths, commit, and timestamp.
- Proposal/approval queue with exact diffs.
- Disclosure history with provider, model, hashes, and character count.
- Rejected-capture history with policy reason but no stored secret payload.
- Explicit controls for validation and index rebuild.
- Clear degraded/attention states in the sidebar and Brain view.

### Acceptance checks

- All endpoints are authenticated.
- Protected execution requires an approval action separate from proposal creation.
- Dashboard renders empty and degraded states.
- Operational controls cannot mutate canonical content except through transactions.

### Rollback

UI can be removed independently; ledger and Git history remain authoritative.

## 6. Upgrade retrieval quality

### Deliverables

- Section-level indexing with note and heading provenance.
- Authority, project-status, lexical relevance, and bounded recency scoring.
- Wikilink neighbor expansion with strict context budgets.
- Contradiction-preserving result grouping.
- Evaluation cases for authority, citation, contradiction, freshness, and leakage.

### Acceptance checks

- Every excerpt maps to a current note hash and heading.
- Higher-authority evidence wins ranking without hiding conflicting evidence.
- Context budget is deterministic.
- Benchmarks report recall and citation correctness.

### Rollback

Rebuild the prior whole-note projection from canonical Markdown.

## 7. Retire legacy memory

### Deliverables

- Keep the one-time Postgres import with provenance and secret filtering.
- Archive or remove runtime `memory_tools`, graphify query, and transcript writer.
- Replace graph-specific evaluation paths with Brain-backed equivalents.
- Remove obsolete environment variables and dependencies.
- Add migration export/rollback documentation.

### Acceptance checks

- Runtime imports contain no graphify dependency.
- No chat turn writes a transcript into canonical memory.
- Migration is one-time, counted, and auditable.
- Existing non-memory Postgres features continue working.

### Rollback

Legacy data remains untouched until the user explicitly archives it.

## 8. Strengthen security

### Deliverables

- Configurable capture redaction and exclusion patterns.
- Provider-specific Brain context policies: allow, deny, or local-only.
- Context disclosure preview endpoint.
- Disclosure retention and purge operations.
- Secret-like values are neither captured nor stored in rejection logs.

### Acceptance checks

- Denied providers receive no Brain context.
- Local Ollama use creates no remote-disclosure record.
- Preview and actual disclosure hashes match.
- Purging operational logs never mutates canonical notes.

### Rollback

Set Brain context policy to `deny` globally while retaining local search.

## 9. Add backup and recovery

### Deliverables

- Validate/configure an optional private Brain Git remote.
- Explicit backup command and authenticated API trigger.
- Export bundle creation without credentials or operational databases.
- Restore validation from clone or bundle into a temporary directory.
- Document corruption recovery and FTS/index reconstruction.

### Acceptance checks

- Backup is never automatic unless explicitly enabled.
- Credentials are never written into receipts or exports.
- A clean restore passes the Brain validator and reproduces HEAD.
- Failure to push cannot corrupt or dirty the local vault.

### Rollback

Remove remote configuration; local nested Git history remains intact.

## 10. Finish release preparation

### Deliverables

- Run supported Python-version matrix where available.
- Add Brain endpoint, watcher, migration, proposal, and recovery integration tests.
- Complete Upgrade 013 notes/notebook and add follow-on lab entries as warranted.
- Update README, architecture, environment, Docker, and release notes.
- Produce a coherent commit map for the user without creating parent commits.

### Acceptance checks

- Backend lint/tests and frontend lint/build pass.
- Brain validator and lifecycle simulations pass.
- Docker configuration parses and mounts the canonical vault.
- Release notes identify migrations, security behavior, and rollback.

### Rollback

Release preparation changes are documentation/test/configuration only; feature
flags permit disabling capture, context injection, watcher, and backup separately.

## Execution log

| Workstream | Status | Evidence |
|---|---|---|
| 1. Test teardown | Partial | Standalone graph closes; sync executor bridges removed. Pytest/plugin shutdown still stalls on Python 3.13. |
| 2. Proposal/approval | Complete | Content-addressed ledger, exact approval, execution receipts, rejection, audit APIs |
| 3. Lifecycle transitions | Complete | Project creation plus approved ship/finish and harvest/fold workflows |
| 4. Obsidian watcher | Complete | Debounced daemon watcher with safe adoption and fail-closed status |
| 5. Audit dashboard | Complete | Proposals, exact diffs, transactions, disclosures, rejections, validate/reindex |
| 6. Retrieval quality | Complete | Section FTS, authority ranking, heading/hash provenance, deterministic budget |
| 7. Legacy retirement | Complete | Removed graphify runtime, transcript writer, memory tools, and tiktoken dependency |
| 8. Security controls | Complete | Provider policies, disclosure preview/purge, secret-free rejection reasons |
| 9. Backup/recovery | Complete | Explicit Git bundle creation and temporary-clone restore validation |
| 10. Release preparation | In progress | Focused tests/build pass; full-suite Python 3.13 teardown remains |
