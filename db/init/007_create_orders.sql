-- Order status is represented as a flat status_kind column plus a nullable
-- status-specific column (delivered_at), mirroring the four-way discriminated
-- union in models/order_status.py (processing/shipped/delivered/cancelled).
-- Only "delivered" currently carries extra data, so a single nullable column
-- covers it; a separate status-events table would be overkill for one
-- status-specific field and would require a join on every order read. If a
-- future status gains its own payload, revisit this as a JSONB column or a
-- proper status-history table instead of adding one nullable column per kind.
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    status_kind TEXT NOT NULL CHECK (status_kind IN ('processing', 'shipped', 'delivered', 'cancelled')),
    delivered_at DATE,
    date DATE NOT NULL,
    total NUMERIC(10, 2) NOT NULL CHECK (total >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status_kind = 'delivered' OR delivered_at IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);

CREATE TRIGGER orders_set_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

-- Order items snapshot name/price at time of purchase (matching orders.json,
-- which repeats the product name/price rather than relying on a live join) —
-- intentional denormalization so historical orders still display correctly
-- even if a product's name or price changes later.
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id),
    name TEXT NOT NULL,
    qty INT NOT NULL CHECK (qty > 0),
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    size TEXT
);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);
