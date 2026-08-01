from app.security import create_access_token, decode_access_token
from services.user_service import authenticate_user

# Known-good cases (seeded in db/init/012_seed_users.sql)
customer_user = authenticate_user("dana.whitfield@example.com", "customer-demo-pass")
print(customer_user)
assert customer_user is not None
assert customer_user.role == "customer"
assert customer_user.customer_id == "cust_001"

staff_user = authenticate_user("staff@rubato.test", "staff-demo-pass")
print(staff_user)
assert staff_user is not None
assert staff_user.role == "staff"
assert staff_user.customer_id is None

assert authenticate_user("dana.whitfield@example.com", "wrong-password") is None
assert authenticate_user("nobody@example.com", "whatever") is None

token = create_access_token(customer_user)
principal = decode_access_token(token)
assert principal.sub == customer_user.id
assert principal.role == "customer"
assert principal.customer_id == "cust_001"

print("All auth checks passed.")
