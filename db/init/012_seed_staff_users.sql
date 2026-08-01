-- Seed credentials for local/demo use only — see README.md for the login
-- examples. Hashed the same way as customers.password_hash (pgcrypto
-- crypt()/gen_salt('bf')), producing standard bcrypt hashes the app's
-- bcrypt-based verify_password() reads directly.
INSERT INTO staff_users (email, password_hash) VALUES
    ('staff@rubato.test', crypt('staff-demo-pass', gen_salt('bf', 10)));
