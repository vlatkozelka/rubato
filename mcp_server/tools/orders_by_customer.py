from typing import List, Optional

from mcp_server.instance import mcp
from models.order_summary import OrderSummary
from services.order_summary_service import get_orders_by_customer


@mcp.tool()
async def get_orders_by_customer_tool(customer_id: str, limit: int = 5, status: Optional[str] = None) -> List[OrderSummary]:
    """
    Look up a customer's recent orders as compact summaries (order ID,
    placed-at date, status, total, item names), newest first. Optionally
    filter by status and cap the number of results with limit (default 5).
    Returns an empty list if the customer has no matching orders.
    """
    return await get_orders_by_customer(customer_id, limit, status)
