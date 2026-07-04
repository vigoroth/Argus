from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

from app.core.config import get_settings


COLLECTION_NAME = "claude_desktop_docs"


def get_pgvector_collection() -> PGVector:
    settings = get_settings()
    embeddings = OpenAIEmbeddings(
        model=settings.embed_model,
        api_key=settings.openai_api_key,
    )
    return PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=settings.database_url,
        use_jsonb=True,
    )


def add_chunks(chunks: list[Document]) -> int:
    store = get_pgvector_collection()
    store.add_documents(chunks)
    return len(chunks)