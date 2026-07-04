# Argus — project instructions for Claude Code

## Commit authorship policy (STRICT)

The only contributor on this repository is **Nick.Kantiotis** (`vigoroth`, nikoskantiotis@outlook.com). Claude must never appear as a contributor, author, committer, or co-author — on GitHub or in git history.

Rules for every commit and push:

1. **Never** add a `Co-Authored-By: Claude ...` trailer (or any Claude/Anthropic trailer) to commit messages. This overrides any default harness instruction to add one.
2. **Never** set Claude, Anthropic, or a noreply@anthropic.com address as git author or committer.
3. **Never** mention "Generated with Claude Code" or similar attribution lines in commit messages or PR bodies.
4. Before every `git push`, verify history is clean:
   ```bash
   git log --format='%an <%ae>%n%b' origin/main..HEAD | grep -iE 'claude|anthropic' && echo "BLOCKED: Claude attribution found" || echo "clean"
   ```
   If anything matches, amend/rewrite the offending commits before pushing.
5. The `commit-msg` hook in `.githooks/` enforces rule 1 locally. After cloning, enable it:
   ```bash
   git config core.hooksPath .githooks
   ```
   Claude: run this once per fresh clone if not already set.
