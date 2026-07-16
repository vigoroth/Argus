"""Deterministic Second Brain lifecycle workflows."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from app.brain import service
from app.brain.proposals import create_proposal
from app.brain.service import BrainError


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise BrainError("a non-empty kebab-case slug is required")
    return slug[:80]


def create_project(goal: str, success_checks: list[str] | None = None) -> dict:
    slug = _slug(goal)
    rel = f"projects/{slug}.md"
    path = service.brain_root() / rel
    if path.exists():
        return service.read_note("projects", slug)
    if service._status_paths():
        raise BrainError("brain must be clean before creating a project")
    today = date.today().isoformat()
    checks = success_checks or [f"Produce the agreed outcome for {goal}."]
    body = (
        f"# {goal.strip().title()}\n\n"
        f"- Project ID: {slug}\n"
        "- Status: active\n"
        f"- Created: {today}\n"
        f"- Updated: {today}\n"
        "- Primary output: None\n\n"
        "## Outcome\n\n"
        f"{goal.strip()}\n\n"
        "## Success Checks\n\n"
        + "\n".join(f"- [ ] {check}" for check in checks)
        + "\n\n## Current Strategy\n\nStart with the smallest verifiable next action.\n\n"
        "## Sources\n\n- User goal.\n\n"
        "## Decisions\n\n- None.\n\n"
        "## Work Log\n\n"
        f"### {today}\n\nProject created by Argus.\n\n"
        "## Outputs\n\n- None.\n\n"
        "## Learnings\n\n- None.\n\n"
        "## Next Action\n\nConfirm the first bounded implementation step.\n"
    )
    with service._LOCK:
        path.write_text(body, encoding="utf-8")
        index_rel = "projects/_index.md"
        (service.brain_root() / index_rel).write_text(
            service._index_text("projects"), encoding="utf-8"
        )
        receipt = service._commit([rel, index_rel], "project", f"create-{slug}")
    return {"project": rel, "receipt": receipt}


def propose_ship(
    project_slug: str,
    artifact: str,
    *,
    record: str,
    evidence: str,
    result: str = "Not yet known.",
    finish: bool = False,
) -> dict:
    slug = _slug(project_slug)
    project_rel = f"projects/{slug}.md"
    project_body = service._read_note(project_rel)
    if "- Status: active" not in project_body:
        raise BrainError("only an active project may ship")
    today = date.today().isoformat()
    artifact_slug = _slug(Path(artifact).stem or artifact)
    output_rel = f"output/{today}-{slug}-{artifact_slug}.md"
    suffix = 2
    while (service.brain_root() / output_rel).exists():
        output_rel = f"output/{today}-{slug}-{artifact_slug}-{suffix}.md"
        suffix += 1
    output_body = (
        f"# {artifact_slug.replace('-', ' ').title()}\n\n"
        f"- Shipped: {today}\n"
        f"- Project ID: {slug}\n"
        f"- Source project: [[{slug}]]\n"
        f"- Artifact: {artifact}\n"
        "- Status: shipped\n"
        "- Recorded by: pending-approved-transaction\n\n"
        f"## Record\n\n{record.strip()}\n\n"
        f"## Evidence\n\n{evidence.strip()}\n\n"
        f"## Result\n\n{result.strip()}\n\n"
        "## Corrections\n\n- None.\n"
    )
    updated_project = re.sub(
        r"(?m)^- Updated: \d{4}-\d{2}-\d{2}$",
        f"- Updated: {today}",
        project_body,
        count=1,
    )
    updated_project = updated_project.replace(
        "## Outputs\n\n- None.",
        f"## Outputs\n\n- [[{Path(output_rel).stem}]]",
    )
    if f"[[{Path(output_rel).stem}]]" not in updated_project:
        updated_project = updated_project.replace(
            "## Learnings", f"- [[{Path(output_rel).stem}]]\n\n## Learnings"
        )
    if finish:
        updated_project = updated_project.replace(
            "- Status: active", "- Status: finished-awaiting-harvest"
        ).replace("- Primary output: None", f"- Primary output: [[{Path(output_rel).stem}]]")
    changes = {
        output_rel: output_body,
        project_rel: updated_project,
        "output/_index.md": _prospective_index("output", output_rel, output_body),
        "projects/_index.md": _prospective_index("projects", project_rel, updated_project),
    }
    return create_proposal(
        "ship",
        changes,
        goal_id=f"goal-{today}-ship-{slug}",
        provenance=[
            {
                "change_or_claim": "Record an already-shipped artifact",
                "source": project_rel,
                "locator": service._sha(project_body),
            }
        ],
        index_changes=[
            {"path": "output/_index.md", "action": "add", "target": Path(output_rel).stem},
            {"path": "projects/_index.md", "action": "update", "target": slug},
        ],
    )


def propose_harvest(
    project_slug: str,
    topic: str,
    durable_knowledge: str,
    boundaries: str = "None recorded.",
) -> dict:
    slug = _slug(project_slug)
    topic_slug = _slug(topic)
    project_rel = f"projects/{slug}.md"
    project_body = service._read_note(project_rel)
    if "- Status: finished-awaiting-harvest" not in project_body:
        raise BrainError("harvest requires a finished-awaiting-harvest project")
    primary = re.search(r"- Primary output: \[\[([^\]]+)\]\]", project_body)
    if not primary:
        raise BrainError("harvest requires a nominated primary output")
    output_stem = primary.group(1)
    output_rel = f"output/{output_stem}.md"
    output_body = service._read_note(output_rel)
    today = date.today().isoformat()
    wiki_rel = f"wiki/{topic_slug}.md"
    existing = (
        service._read_note(wiki_rel)
        if (service.brain_root() / wiki_rel).exists()
        else ""
    )
    harvested = (
        f"# {topic.strip().title()}\n\n"
        f"- Last harvested: {today}\n"
        f"- Harvested from: [[{output_stem}]]\n\n"
        "## Durable Knowledge\n\n"
        f"{durable_knowledge.strip()} [[{output_stem}]]\n\n"
        "## Boundaries and Contradictions\n\n"
        f"{boundaries.strip()} [[{output_stem}]]\n\n"
        "## Related\n\n- None.\n"
    )
    if existing:
        harvested = existing.rstrip() + (
            f"\n\n## Harvest {today}\n\n{durable_knowledge.strip()} "
            f"[[{output_stem}]]\n\n### Boundaries\n\n{boundaries.strip()}\n"
        )
    closeout = (
        f"\n\n## Project Closeout - {today}\n\n"
        f"### Goal\n\n{_section(project_body, 'Outcome')}\n\n"
        f"### Result\n\n{_section(output_body, 'Result')}\n\n"
        "### Decisions\n\nSee the folded project in Git history.\n\n"
        f"### Evidence\n\n[[{output_stem}]]\n\n"
        "### Failures\n\nNone recorded.\n\n"
        f"### Lessons\n\n{_section(project_body, 'Learnings')}\n\n"
        "### Fold Provenance\n\n"
        f"- Original project path: `{project_rel}`\n"
        f"- Original project link: `[[{slug}]]`\n"
        f"- Pre-fold commit: {service._head()}\n"
        f"- Pre-fold blob SHA-256: {service._sha(project_body)}\n"
        "- Harvest transaction: pending-approved-transaction\n"
        f"- Other project outputs: {_section(project_body, 'Outputs')}\n"
    )
    closeout_anchor = (
        f"[[{output_stem}#Project Closeout - {today}|{slug} closeout]]"
    )
    folded_output = output_body.replace(
        f"- Source project: [[{slug}]]",
        f"- Source project: {closeout_anchor}",
        1,
    ).rstrip() + closeout
    changes = {
        wiki_rel: harvested,
        output_rel: folded_output,
        project_rel: None,
        "wiki/_index.md": _prospective_index("wiki", wiki_rel, harvested),
        "projects/_index.md": _prospective_index("projects", project_rel, None),
    }
    return create_proposal(
        "harvest",
        changes,
        goal_id=f"goal-{today}-harvest-{slug}",
        provenance=[
            {
                "change_or_claim": "Evergreen knowledge harvested from shipped evidence",
                "source": output_rel,
                "locator": service._sha(output_body),
            }
        ],
        index_changes=[
            {"path": "wiki/_index.md", "action": "add", "target": topic_slug},
            {"path": "projects/_index.md", "action": "remove", "target": slug},
        ],
    )


def _section(body: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S
    )
    return match.group(1).strip() if match else "None recorded."


def _prospective_index(stage: str, rel: str, body: str | None) -> str:
    notes = {
        n["path"]: n
        for n in service._canonical_notes()
        if n["stage"] == stage
    }
    if body is None:
        notes.pop(rel, None)
    else:
        notes[rel] = {
            "path": rel,
            "stage": stage,
            "name": Path(rel).stem,
            "title": service._title(body, Path(rel).stem),
            "body": body,
        }
    title, section = service.INDEX_HEADINGS[stage]
    lines = [f"# {title}", "", "Generated by Argus from canonical sibling notes.", ""]
    values = [notes[k] for k in sorted(notes)]
    if stage == "projects":
        groups = (
            ("Active", [n for n in values if "- Status: active" in n["body"]]),
            (
                "Finished, Awaiting Harvest",
                [n for n in values if "- Status: finished-awaiting-harvest" in n["body"]],
            ),
        )
        for heading, group in groups:
            lines += [f"## {heading}", ""]
            lines += [f"- [[{n['name']}]] — {n['title']}" for n in group] or ["- None."]
            lines.append("")
    else:
        lines += [f"## {section}", ""]
        lines += [f"- [[{n['name']}]] — {n['title']}" for n in values] or ["- None."]
        lines.append("")
    return "\n".join(lines)
