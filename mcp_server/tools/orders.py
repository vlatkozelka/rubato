from typing import Optional

from mcp_server.instance import mcp
from models.order import Order
from services.order_service import get_order_by_id


@mcp.tool()
async def get_order_by_id_tool(order_id: str) -> Optional[Order]:
    """
    Look up an order by its ID, including its line items and status.
    Returns None if no order with that ID exists.
    """
    return await get_order_by_id(order_id)
