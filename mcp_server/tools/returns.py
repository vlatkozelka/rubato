from typing import Optional

from mcp_server.instance import mcp
from models.order_item import OrderItem
from services.return_service import initiate_return


@mcp.tool()
async def initiate_return_tool(order_id: str, product_id: str, customer_id: str, reason: str) -> Optional[OrderItem]:
    """
    Start a return for a specific item on an order. Returns the returned
    OrderItem, or None if the order/customer/product combination is invalid.
    """
    return await initiate_return(order_id, product_id, customer_id, reason)
