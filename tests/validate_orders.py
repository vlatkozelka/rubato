import asyncio

from services.order_service import get_order_by_id
from services.customer_service import get_customer_by_id

# Known-good cases
order = asyncio.run(get_order_by_id("ord_1002"))
print(order)
assert order is not None
assert order.customer_id == "cust_002"

assert asyncio.run(get_order_by_id("ord_9999")) is None

print("All structured lookup checks passed.")