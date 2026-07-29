CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_chunks (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    source TEXT NOT NULL,
    chunk_index INT NOT NULL,
    strategy TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL
);