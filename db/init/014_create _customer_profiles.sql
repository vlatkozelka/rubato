CREATE TABLE customer_profiles (
    customer_id         TEXT PRIMARY KEY REFERENCES customers(id),
    refund_request_count INTEGER NOT NULL DEFAULT 0,
    last_contacted_at    TIMESTAMPTZ,
    notes                TEXT
);