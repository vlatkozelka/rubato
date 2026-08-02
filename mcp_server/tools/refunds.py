from typing import Optional

from mcp_server.instance import mcp
from models.approval import Approval
from services.refund_service import check_refund


@mcp.tool()
async def check_refund_tool(order_id: str, product_id: str, customer_id: str, reason: str) -> Optional[Approval]:
    """
    Evaluate a refund request against the order's delivery status and the
    applicable refund policy window. Returns an Approval (pending review or
    denied), or None if the order/customer/product combination is invalid.
    """
    return await check_refund(order_id, product_id, customer_id, reason)
