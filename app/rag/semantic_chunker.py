"""Semantic chunking — split documents where meaning shifts, using
embedding similarity between sentences, instead of fixed character sizes.
"""
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

from app.core.config import get_settings


def semantic_chunk(docs: list[Document]) -> list[Document]:
    """Split documents at semantic boundaries (topic shifts)."""
    settings = get_settings()
    embeddings = OpenAIEmbeddings(
        model=settings.embed_model,
        api_key=settings.openai_api_key,
    )
    splitter = SemanticChunker(
        embeddings,
        breakpoint_threshold_type="percentile",
    )
    chunks = splitter.split_documents(docs)
    for i, c in enumerate(chunks):
        c.metadata["chunk_index"] = i
    return chunks