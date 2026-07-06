"""add_idea: appends rows to the lab backlog table (Upgrade 005)."""
from app.tools import idea_tools

TABLE = """# Ideas

| Idea | Category | Why it's worth learning | Effort | Status |
|------|----------|-------------------------|--------|--------|
| Existing thing | rag | reasons | 🟡 | idea |

## Raw notes

-
"""


def _setup(tmp_path, monkeypatch, text=TABLE):
    f = tmp_path / "IDEAS.md"
    f.write_text(text)
    monkeypatch.setattr(idea_tools, "IDEAS_MD", f)
    return f


def test_append_lands_in_table(tmp_path, monkeypatch):
    f = _setup(tmp_path, monkeypatch)
    out = idea_tools.add_idea.invoke(
        {"idea": "New idea", "category": "agent", "why": "learning", "effort": "small"})
    assert "recorded" in out
    text = f.read_text()
    row = "| New idea | agent | learning | 🟢 | idea |"
    assert row in text
    # row sits inside the table, above Raw notes
    assert text.index(row) < text.index("## Raw notes")
    assert text.index("| Existing thing") < text.index(row)


def test_effort_mapping_defaults_medium(tmp_path, monkeypatch):
    f = _setup(tmp_path, monkeypatch)
    idea_tools.add_idea.invoke(
        {"idea": "X", "category": "perf", "why": "y", "effort": "nonsense"})
    assert "| X | perf | y | 🟡 | idea |" in f.read_text()


def test_bad_category(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    out = idea_tools.add_idea.invoke(
        {"idea": "X", "category": "astrology", "why": "y", "effort": "small"})
    assert out.startswith("ERROR")


def test_pipe_sanitized(tmp_path, monkeypatch):
    f = _setup(tmp_path, monkeypatch)
    idea_tools.add_idea.invoke(
        {"idea": "A | B", "category": "ml", "why": "w", "effort": "large"})
    assert "| A / B | ml | w | 🔴 | idea |" in f.read_text()


def test_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(idea_tools, "IDEAS_MD", tmp_path / "nope.md")
    out = idea_tools.add_idea.invoke(
        {"idea": "X", "category": "ml", "why": "y", "effort": "small"})
    assert out.startswith("ERROR")
