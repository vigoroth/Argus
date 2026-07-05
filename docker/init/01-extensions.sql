-- Runs once, on first initialization of a fresh Postgres data volume.
-- The FTS column/index on langchain_pg_embedding is added after the first RAG
-- ingest (the table is created lazily by pgvector) — see README.
CREATE EXTENSION IF NOT EXISTS vector;
