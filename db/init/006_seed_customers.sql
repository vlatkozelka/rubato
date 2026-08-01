-- Generated from data/customers.json (pre-migration source of truth).
-- password_hash uses the same fixed demo password for every seeded customer,
-- hashed via pgcrypto so no Python step is needed to seed from scratch — see
-- db/init/011_create_staff_users.sql for the equivalent staff-side note.
INSERT INTO customers (id, name, email, password_hash, tier) VALUES
    ('cust_001', 'Dana Whitfield', 'dana.whitfield@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'standard'),
    ('cust_002', 'Marcus Ito', 'marcus.ito@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'vip'),
    ('cust_003', 'Priya Nair', 'priya.nair@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'standard'),
    ('cust_004', 'Sofia Beltran', 'sofia.beltran@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'standard'),
    ('cust_005', 'Tomas Weber', 'tomas.weber@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'vip'),
    ('cust_006', 'Lena Farrow', 'lena.farrow@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'standard');
