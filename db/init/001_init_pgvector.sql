CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_chunks (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    source TEXT NOT NULL,
    chunk_index INT NOT NULL,
    strategy TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en',
    embedding VECTOR(1024) NOT NULL,
    text_search tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED
);

CREATE INDEX policy_chunks_text_search_idx ON policy_chunks USING GIN (text_search);