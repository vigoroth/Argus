from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_documents(
    documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[Document]:
    """Chunk a list of documents into smaller pieces.

    Args:
        documents: The list of documents to chunk.
        chunk_size: The maximum size of each chunk.
        chunk_overlap: The number of characters to overlap between chunks.

    Returns:
        A list of chunked documents.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = splitter.split_documents(documents)

    # tag each chunk with its index so we can trace it back later
    for i, c in enumerate(chunks):
        c.metadata["chunk_index"] = i

    return chunks