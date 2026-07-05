"""Reciprocal Rank Fusion ordering in app/rag/hybrid.py.

The module imports psycopg at top level; skip cleanly where it's unavailable.
"""
import pytest

pytest.importorskip("psycopg", reason="app.rag.hybrid imports psycopg at module load")

from app.rag.hybrid import _rrf_fuse  # noqa: E402


def test_agreed_top_ranks_first():
    # a doc ranked highly in BOTH lists should win the fusion
    dense = ["A", "B", "C"]
    sparse = ["A", "C", "B"]
    fused = _rrf_fuse(dense, sparse)
    assert fused[0] == "A"


def test_dedupes_across_lists():
    fused = _rrf_fuse(["A", "B"], ["B", "A"])
    assert sorted(fused) == ["A", "B"]
    assert len(fused) == 2


def test_unique_docs_all_present():
    fused = _rrf_fuse(["A", "B"], ["C", "D"])
    assert set(fused) == {"A", "B", "C", "D"}


def test_higher_rank_beats_lower_rank():
    # a doc only in dense at rank 0 beats a doc only in sparse at rank 5
    dense = ["X"]
    sparse = ["a", "b", "c", "d", "e", "Y"]
    fused = _rrf_fuse(dense, sparse)
    assert fused.index("X") < fused.index("Y")
