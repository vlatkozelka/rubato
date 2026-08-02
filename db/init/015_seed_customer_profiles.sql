INSERT INTO customer_profiles (customer_id, refund_request_count, last_contacted_at, notes) VALUES
    ('cust_001', 3, now() - interval '1 day',  'Flagged as frequent refund requester — 3 requests in the past 30 days.'),
    ('cust_002', 0, now() - interval '10 days', NULL),
    ('cust_003', 1, now() - interval '2 days',  NULL),
    ('cust_004', 0, NULL,                        NULL),
    ('cust_005', 5, now() - interval '3 days',  'Flagged as frequent refund requester — 5 requests in the past 30 days.'),
    ('cust_006', 1, now() - interval '5 days',  NULL);