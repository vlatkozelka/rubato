from mcp_server.instance import mcp
from models.approval import Approval, ApprovalPayload
from services.approval_service import create_approval


@mcp.tool()
async def create_pending_approval_tool(payload: ApprovalPayload) -> Approval:
    """
    Submit a refund/return request for human review. This does NOT
    approve, execute, or process anything — it creates a PENDING record
    that a human must separately approve before any money moves or any
    action is taken.

    After calling this, you have NOT refunded, approved, or resolved
    the customer's case. You have only queued it for review. Your
    reply to the customer must reflect that the request is pending,
    not that it has been completed.
    """
    return await create_approval(payload)
