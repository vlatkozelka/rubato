-- Seed credentials for local/demo use only — this is a portfolio sandbox,
-- not a real auth system, so passwords are fixed and documented rather than
-- generated through a registration flow. See README.md for the login
-- examples. Hashes are computed here with pgcrypto's crypt()/gen_salt('bf'),
-- which produces standard bcrypt-format hashes ($2a$...) that the app's
-- bcrypt-based verify_password() reads directly — no Python step needed to
-- seed a real database from scratch.
INSERT INTO users (email, password_hash, role, customer_id) VALUES
    ('staff@rubato.test', crypt('staff-demo-pass', gen_salt('bf', 10)), 'staff', NULL);

INSERT INTO users (email, password_hash, role, customer_id) VALUES
    ('dana.whitfield@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'customer', 'cust_001'),
    ('marcus.ito@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'customer', 'cust_002'),
    ('priya.nair@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'customer', 'cust_003'),
    ('sofia.beltran@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'customer', 'cust_004'),
    ('tomas.weber@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'customer', 'cust_005'),
    ('lena.farrow@example.com', crypt('customer-demo-pass', gen_salt('bf', 10)), 'customer', 'cust_006');
