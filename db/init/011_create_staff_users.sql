-- Staff accounts are a separate table from customers rather than a shared
-- users table with a role discriminator (see the superseded decision in
-- DECISIONS.md). Staff aren't customers, share nothing with the customers
-- table beyond "has a password", and this table has no FK back to
-- customers at all — membership in this table is itself the role, so no
-- role column is needed either.
CREATE TABLE IF NOT EXISTS staff_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER staff_users_set_updated_at
BEFORE UPDATE ON staff_users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
