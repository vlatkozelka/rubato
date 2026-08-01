from app.security import create_access_token, decode_access_token
from models.user_role import UserRole
from services.customer_auth_service import authenticate_customer
from services.staff_auth_service import authenticate_staff

# Known-good cases (seeded in db/init/006_seed_customers.sql and
# db/init/012_seed_staff_users.sql)
customer = authenticate_customer("dana.whitfield@example.com", "customer-demo-pass")
print(customer)
assert customer is not None
assert customer.id == "cust_001"

staff = authenticate_staff("staff@rubato.test", "staff-demo-pass")
print(staff)
assert staff is not None

assert authenticate_customer("dana.whitfield@example.com", "wrong-password") is None
assert authenticate_customer("nobody@example.com", "whatever") is None
assert authenticate_staff("dana.whitfield@example.com", "customer-demo-pass") is None
assert authenticate_staff("staff@rubato.test", "wrong-password") is None

customer_token = create_access_token(customer.id, UserRole.CUSTOMER)
customer_principal = decode_access_token(customer_token)
assert customer_principal.sub == customer.id
assert customer_principal.role == UserRole.CUSTOMER
assert customer_principal.customer_id == customer.id

staff_token = create_access_token(staff.id, UserRole.STAFF)
staff_principal = decode_access_token(staff_token)
assert staff_principal.sub == staff.id
assert staff_principal.role == UserRole.STAFF
assert staff_principal.customer_id is None

print("All auth checks passed.")
