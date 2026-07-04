"""Module 4 demo: ingest a document into the vector store.

Run:  python -m app.rag.ingest_demo
"""
from app.rag.loader import load_document
from app.rag.chunker import chunk_documents
from app.rag.store import add_chunks


def main() -> None:
    # make a sample doc to ingest
    sample = "/tmp/sample_rag.md"
    with open(sample, "w") as f:
        f.write(
            "# Job Hunting Tips\n\n"
            "Tailor your resume to each role. Use keywords from the job description.\n\n"
            "Network actively. Most jobs are filled through referrals, not applications.\n\n"
            "Prepare stories using the STAR method: Situation, Task, Action, Result.\n\n"
            "For technical roles, build a portfolio project that demonstrates real skills.\n"
        )

    docs = load_document(sample)
    print(f"loaded {len(docs)} document(s)")

    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=40)
    print(f"split into {len(chunks)} chunk(s)")

    n = add_chunks(chunks)
    print(f"stored {n} chunk(s) in pgvector")


if __name__ == "__main__":
    main()