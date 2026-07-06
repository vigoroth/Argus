"""Skills loader: frontmatter parsing, progressive-disclosure index, and the
draft → approve/reject gate (Upgrade 004). Pure filesystem, no LLM."""
import pytest

from app.skills import loader


@pytest.fixture()
def skills_dir(tmp_path, monkeypatch):
    root = tmp_path / "skills"
    root.mkdir()
    monkeypatch.setattr(loader, "SKILLS_DIR", root)
    monkeypatch.setattr(loader, "PENDING_DIR", root / "_pending")
    return root


def _mk(root, name, description="d", body="Body text."):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n")


def test_parse_frontmatter(skills_dir):
    _mk(skills_dir, "alpha", "when testing alpha", "Do the alpha thing.")
    s = loader.parse_skill(skills_dir / "alpha" / "SKILL.md")
    assert s["name"] == "alpha"
    assert s["description"] == "when testing alpha"
    assert s["body"].strip() == "Do the alpha thing."


def test_parse_no_frontmatter_falls_back_to_dirname(skills_dir):
    d = skills_dir / "bare"
    d.mkdir()
    (d / "SKILL.md").write_text("Just a body, no fences.")
    s = loader.parse_skill(d / "SKILL.md")
    assert s["name"] == "bare"
    assert s["body"] == "Just a body, no fences."


def test_index_lists_live_only(skills_dir):
    _mk(skills_dir, "alpha", "trigger a")
    _mk(skills_dir, "beta", "trigger b")
    _mk(skills_dir, "_pending/hidden", "never")
    idx = loader.skill_index()
    assert "- alpha: trigger a" in idx and "- beta: trigger b" in idx
    assert "hidden" not in idx


def test_load_skill(skills_dir):
    _mk(skills_dir, "alpha", body="Full instructions.")
    assert loader.load_skill("alpha").strip() == "Full instructions."
    assert loader.load_skill("nope") is None
    assert loader.load_skill("../etc") is None  # traversal guard


def test_draft_approve_roundtrip(skills_dir):
    loader.draft_skill("new-one", "when new", "How-to.")
    assert [p["name"] for p in loader.list_pending()] == ["new-one"]
    assert loader.load_skill("new-one") is None          # not live yet
    assert loader.approve_skill("new-one") is True
    assert loader.list_pending() == []
    assert loader.load_skill("new-one").strip() == "How-to."
    assert loader.approve_skill("new-one") is False      # nothing pending anymore


def test_reject_deletes_draft(skills_dir):
    loader.draft_skill("bad-idea", "no", "nope")
    assert loader.reject_skill("bad-idea") is True
    assert loader.list_pending() == []
    assert loader.load_skill("bad-idea") is None
    assert loader.reject_skill("bad-idea") is False


def test_slug_validation(skills_dir):
    with pytest.raises(ValueError):
        loader.draft_skill("../evil", "x", "y")
    with pytest.raises(ValueError):
        loader.draft_skill("Bad Name", "x", "y")
    assert loader.approve_skill("../evil") is False
    assert loader.reject_skill("../evil") is False


def test_draft_duplicate_of_live_rejected(skills_dir):
    _mk(skills_dir, "alpha")
    with pytest.raises(ValueError):
        loader.draft_skill("alpha", "x", "y")
