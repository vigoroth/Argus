"""Chunking behavior in app/rag/chunker.py."""
from langchain_core.documents import Document

from app.rag.chunker import chunk_documents


def test_short_doc_single_chunk():
    doc = Document(page_content="short text", metadata={"source": "a.txt"})
    chunks = chunk_documents([doc], chunk_size=1000, chunk_overlap=200)
    assert len(chunks) == 1
    assert chunks[0].page_content == "short text"


def test_long_doc_splits():
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_documents([Document(page_content=text)], chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(len(c.page_content) <= 200 for c in chunks)


def test_chunk_index_is_tagged_sequentially():
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_documents([Document(page_content=text)], chunk_size=200, chunk_overlap=20)
    assert [c.metadata["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_source_metadata_preserved():
    doc = Document(page_content="x " * 500, metadata={"source": "src.md"})
    chunks = chunk_documents([doc], chunk_size=100, chunk_overlap=10)
    assert all(c.metadata["source"] == "src.md" for c in chunks)
