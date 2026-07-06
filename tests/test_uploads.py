"""Upload store: sanitization, collision handling, round-trip (Upgrade 010)."""
import pytest

from app.web import uploads


@pytest.fixture()
def updir(tmp_path, monkeypatch):
    d = tmp_path / "uploads"
    monkeypatch.setattr(uploads, "UPLOADS_DIR", d)
    return d


def test_safe_filename():
    assert uploads.safe_filename("../../etc/passwd") == "passwd"
    assert uploads.safe_filename("my data (v2).csv") == "my_data_v2_.csv"  # runs collapse
    assert uploads.safe_filename(".hidden.csv") == "hidden.csv"
    assert uploads.safe_filename("x" * 300 + ".csv")[:120]  # capped
    assert uploads.safe_filename("") == "upload"


def test_allowed():
    assert uploads.allowed("a.csv") and uploads.allowed("b.XLSX") and uploads.allowed("c.sqlite")
    for bad in ("evil.py", "run.sh", "noext"):
        assert not uploads.allowed(bad)


def test_save_list_delete_roundtrip(updir):
    p = uploads.save_upload("sales.csv", b"a,b\n1,2\n")
    assert p.read_bytes() == b"a,b\n1,2\n"
    p2 = uploads.save_upload("sales.csv", b"other")   # collision -> suffixed
    assert p2.name == "sales_1.csv"
    names = [f["name"] for f in uploads.list_uploads()]
    assert names == ["sales.csv", "sales_1.csv"]
    assert uploads.delete_upload("sales.csv") is True
    assert [f["name"] for f in uploads.list_uploads()] == ["sales_1.csv"]
    assert uploads.delete_upload("nope.csv") is False


def test_delete_traversal_neutralized(updir):
    (updir).mkdir(parents=True)
    outside = updir.parent / "secret.csv"
    outside.write_text("x")
    # "../secret.csv" sanitizes to "secret.csv" INSIDE uploads dir -> not found
    assert uploads.delete_upload("../secret.csv") is False
    assert outside.exists()
