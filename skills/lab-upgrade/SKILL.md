---
name: lab-upgrade
description: Use when asked to build, ship, or log a project upgrade/feature for Argus — follows the lab process end to end.
---

# Lab upgrade process

Every Argus upgrade is educational and follows this exact loop. Work from the repo root.

1. **Pick** — read `lab/IDEAS.md`; choose a row marked `next` (or the user's request).
2. **Scaffold** — `python lab/lab.py new "<Title>"` → creates
   `lab/upgrades/NNN-<slug>/{notes.md,notebook.ipynb}` and syncs the README log.
3. **Build** — implement in `app/`; reuse existing patterns (tool style:
   `app/tools/calendar_tools.py`; auth-gated endpoints: calendar routes in
   `app/web/server.py`; lazy views: `CalendarView`).
4. **Test** — add `tests/test_<feature>.py`; run `python -m pytest -q` (must stay green)
   and `ruff check .` (must be clean). Frontend touched → `npm run build` in
   `app/web/frontend`.
5. **Document** — fill `notes.md` (Concept/theory section is the point of the lab);
   demonstrate the core mechanism in `notebook.ipynb` and execute it.
6. **Sync** — `python lab/lab.py sync`; update the idea's Status in `lab/IDEAS.md`.

Rules: ask before destructive commands; never commit/push unless the user asks;
`lab/` is private (gitignored) — keep it that way.
