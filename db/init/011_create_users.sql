-- Single users table with a role discriminator (staff/customer) rather than
-- two parallel tables (e.g. staff_users + a customers-linked table). Staff
-- and customer accounts share the exact same auth surface (email,
-- password_hash, timestamps) and go through one login endpoint; the only
-- difference is a nullable link to customers, which one column expresses
-- fine. This mirrors the status_kind + nullable-column pattern already used
-- for orders rather than introducing a second parallel schema.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('staff', 'customer')),
    customer_id TEXT REFERENCES customers(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((role = 'customer') = (customer_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_users_customer_id ON users(customer_id);

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
