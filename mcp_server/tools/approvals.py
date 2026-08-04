from typing import Optional

from mcp_server.instance import mcp
from models.approval import Approval, ApprovalStatus, ApprovalType
from services.approval_service import create_approval


@mcp.tool()
async def create_approval_tool(
    order_id: str,
    reason: str,
    type: ApprovalType,
    status: ApprovalStatus,
    customer_id: str,
    amount: Optional[float] = None,
) -> Approval:
    """
    Persist a new approval record (e.g. a pending refund request) and
    return it as stored.
    """
    return await create_approval(
        order_id=order_id,
        reason=reason,
        amount=amount,
        type=type,
        status=status,
        customer_id=customer_id,
    )
