from typing import List

from mcp_server.instance import mcp
from models.order import Order
from services.orders_by_ids_service import get_orders_by_ids


@mcp.tool()
async def get_orders_by_ids_tool(order_ids: List[str], customer_id: str) -> List[Order]:
    """
    Look up multiple orders at once by ID, each including its line items
    and status. Order IDs that don't exist, or that don't belong to the
    given customer, are silently omitted from the result rather than
    causing an error.
    """
    return await get_orders_by_ids(order_ids, customer_id)
