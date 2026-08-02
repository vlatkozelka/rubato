CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL REFERENCES customers(id),
    history         JSONB NOT NULL DEFAULT '[]',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);