from services.order_service import get_order_by_id
from services.customer_service import get_customer_by_id

# Known-good cases
customer = get_customer_by_id("cust_002")
print(customer)
assert customer is not None
assert customer.id == "cust_002"
assert customer.tier == "vip"

assert get_customer_by_id("jkdjaslkdjla") is None

print("All structured lookup checks passed.")