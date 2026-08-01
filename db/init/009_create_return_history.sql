-- Flattened from data/return_history.json, which grouped returns by
-- customer_id; one row per return here instead, since customer_id is
-- already a queryable column and the nested-list shape added nothing.
CREATE TABLE IF NOT EXISTS return_history (
    id SERIAL PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    order_id TEXT NOT NULL REFERENCES orders(id),
    product_id TEXT NOT NULL REFERENCES products(id),
    reason TEXT NOT NULL CHECK (reason IN ('changed_mind', 'wrong_size', 'defective', 'other')),
    requested_at DATE NOT NULL,
    resolution TEXT NOT NULL CHECK (resolution IN ('refunded', 'exchanged', 'denied')),
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0)
);

CREATE INDEX IF NOT EXISTS idx_return_history_customer_id ON return_history(customer_id);
CREATE INDEX IF NOT EXISTS idx_return_history_order_id ON return_history(order_id);
