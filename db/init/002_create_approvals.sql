CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL CHECK (type IN ('refund_request')),
    status TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (status IN ('pending_review', 'approved', 'denied')),
    payload JSONB NOT NULL,
    reason TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_approvals_customer_id ON approvals(customer_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER approvals_set_updated_at
BEFORE UPDATE ON approvals
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();