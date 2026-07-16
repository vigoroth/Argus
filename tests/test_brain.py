import subprocess
from pathlib import Path

import pytest

from app.brain import service
from app.brain.backup import create_bundle
from app.brain.proposals import (
    approve_proposal,
    create_proposal,
    execute_proposal,
    get_proposal,
)
from app.brain.workflows import create_project, propose_harvest, propose_ship


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture()
def brain(tmp_path, monkeypatch):
    root = tmp_path / "brain"
    root.mkdir()
    for stage, heading, section in (
        ("inbox", "Inbox Index", "Items"),
        ("projects", "Projects Index", "Active"),
        ("output", "Output Index", "Shipped Outputs"),
        ("wiki", "Wiki Index", "Articles"),
    ):
        folder = root / stage
        folder.mkdir()
        text = f"# {heading}\n\n## {section}\n\n- None.\n"
        if stage == "projects":
            text += "\n## Finished, Awaiting Harvest\n\n- None.\n"
        (folder / "_index.md").write_text(text)
    _git(root, "init")
    _git(root, "add", "--", "inbox/_index.md", "projects/_index.md",
         "output/_index.md", "wiki/_index.md")
    _git(
        root, "-c", "user.name=Test", "-c", "user.email=test@example.com",
        "commit", "-m", "bootstrap",
    )
    monkeypatch.setattr(service, "brain_root", lambda: root)
    monkeypatch.setattr(service, "_ops_db", lambda: tmp_path / "brain.sqlite")
    return root


def test_capture_creates_indexed_commit(brain):
    result = service.capture_message("Remember that my cat is named Mochi.")
    assert result and result["note"].startswith("inbox/")
    assert (brain / result["note"]).is_file()
    assert "[[" in (brain / "inbox/_index.md").read_text()
    assert not _git(brain, "status", "--porcelain")
    assert _git(brain, "log", "-1", "--pretty=%s").startswith("brain(capture):")


def test_capture_excludes_questions_and_secrets(brain):
    assert service.capture_message("Do you remember my name?") is None
    assert service.capture_message("Remember my API key is sk-abcdefghijklmnop") is None
    assert _git(brain, "rev-list", "--count", "HEAD") == "1"


def test_query_prefers_wiki_authority(brain):
    (brain / "inbox/raw.md").write_text("# Raw\n\nArgus architecture uses a compass.\n")
    (brain / "wiki/argus-architecture.md").write_text(
        "# Argus Architecture\n\nArgus architecture uses a compass.\n"
    )
    for stage in ("inbox", "wiki"):
        (brain / stage / "_index.md").write_text(service._index_text(stage))
    _git(brain, "add", "--", "inbox/raw.md", "inbox/_index.md",
         "wiki/argus-architecture.md", "wiki/_index.md")
    _git(
        brain, "-c", "user.name=Test", "-c", "user.email=test@example.com",
        "commit", "-m", "notes",
    )
    results = service.query_brain("Argus architecture compass")
    assert results[0]["stage"] == "wiki"
    assert results[0]["wikilink"] == "[[argus-architecture]]"
    assert results[0]["heading"] in {"Argus Architecture", "Raw"}


def test_dirty_external_edit_blocks_capture(brain):
    (brain / "inbox/manual.md").write_text("# Manual\n")
    with pytest.raises(service.BrainError, match="uncommitted external edits"):
        service.capture_message("Remember that I prefer Python.")


def test_obsidian_uri_is_encoded(brain):
    uri = service.obsidian_uri("projects/my note.md")
    assert uri.startswith("obsidian://open?path=")
    assert "%20" in uri and "%2F" in uri


def test_proposal_approval_is_hash_and_base_bound(brain):
    body = "# Shipped\n\n- Shipped: 2026-07-16\n"
    proposal = create_proposal(
        "ship",
        {"output/2026-07-16-demo.md": body},
        goal_id="goal-2026-07-16-demo-a1b2c3d4",
    )
    with pytest.raises(service.BrainError, match="hash"):
        approve_proposal(proposal["proposal_id"], "sha256:" + "0" * 64)
    approve_proposal(proposal["proposal_id"], proposal["diff_hash"])
    receipt = execute_proposal(proposal["proposal_id"])
    assert receipt["paths"] == ["output/2026-07-16-demo.md"]
    assert get_proposal(proposal["proposal_id"])["state"] == "executed"
    with pytest.raises(service.BrainError, match="requires exact approval"):
        execute_proposal(proposal["proposal_id"])


def test_project_and_ship_workflow(brain):
    created = create_project("Build memory audit")
    assert created["project"] == "projects/build-memory-audit.md"
    proposal = propose_ship(
        "build-memory-audit",
        "report.md",
        record="A report was delivered.",
        evidence="The local artifact exists.",
        finish=True,
    )
    assert proposal["operation"] == "ship"
    assert "output/_index.md" in proposal["paths"]
    approve_proposal(proposal["proposal_id"], proposal["diff_hash"])
    execute_proposal(proposal["proposal_id"])
    project = (brain / "projects/build-memory-audit.md").read_text()
    assert "- Status: finished-awaiting-harvest" in project


def test_harvest_folds_finished_project(brain):
    create_project("Harvest demo")
    project_path = brain / "projects/harvest-demo.md"
    project_path.write_text(
        project_path.read_text().replace(
            "## Learnings\n\n- None.",
            "## Learnings\n\nUse exact hashes for protected transitions.",
        )
    )
    _git(brain, "add", "--", "projects/harvest-demo.md")
    _git(
        brain, "-c", "user.name=Test", "-c", "user.email=test@example.com",
        "commit", "-m", "learning",
    )
    ship = propose_ship(
        "harvest-demo",
        "evidence.md",
        record="The evidence record shipped.",
        evidence="Verified locally.",
        finish=True,
    )
    approve_proposal(ship["proposal_id"], ship["diff_hash"])
    execute_proposal(ship["proposal_id"])
    harvest = propose_harvest(
        "harvest-demo",
        "protected-transitions",
        "Use exact hashes for protected transitions.",
    )
    approve_proposal(harvest["proposal_id"], harvest["diff_hash"])
    execute_proposal(harvest["proposal_id"])
    assert not project_path.exists()
    assert (brain / "wiki/protected-transitions.md").is_file()
    assert service.validate_vault() == []


def test_protected_path_binding(brain):
    with pytest.raises(service.BrainError, match="wiki paths require"):
        create_proposal(
            "ship",
            {"wiki/unsafe.md": "# Unsafe\n"},
            goal_id="goal-2026-07-16-unsafe-a1b2c3d4",
        )


def test_provider_policy_can_deny_remote_context(brain, monkeypatch):
    (brain / "wiki/preference.md").write_text("# Preference\n\nUser prefers local models.\n")
    (brain / "wiki/_index.md").write_text(service._index_text("wiki"))
    _git(brain, "add", "--", "wiki/preference.md", "wiki/_index.md")
    _git(
        brain, "-c", "user.name=Test", "-c", "user.email=test@example.com",
        "commit", "-m", "preference",
    )
    settings = service.get_settings()
    monkeypatch.setattr(settings, "argus_brain_remote_context", "deny")
    preview = service.preview_context("preferred models", "openai", "gpt-test")
    assert preview["permitted"] is False
    assert service.prepare_context("preferred models", "openai", "gpt-test") == ""
    local = service.preview_context("preferred models", "ollama", "local")
    assert local["permitted"] is True


def test_backup_bundle_roundtrip(brain, tmp_path):
    result = create_bundle(str(tmp_path / "backups"))
    assert Path(result["path"]).is_file()
    assert result["validation"]["valid"] is True
    assert result["validation"]["restored_head"] == _git(brain, "rev-parse", "HEAD")
