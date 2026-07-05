from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


def load_document(path: str) -> list[Document]:
    """Load a file into a list of LangChain Document objects.

    Supports .txt, .md, and .pdf. Each Document has page_content (the text)
    and metadata (source path, page number for PDFs).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"no such file: {path}")

    suffix = p.suffix.lower()

    if suffix in {".txt", ".md"}:
        text = p.read_text(encoding="utf-8")
        return [Document(page_content=text, metadata={"source": str(p)})]

    if suffix == ".pdf":
        # PyPDFLoader returns one Document per page, with page numbers in metadata
        return PyPDFLoader(str(p)).load()

    raise ValueError(f"unsupported file type: {suffix}")