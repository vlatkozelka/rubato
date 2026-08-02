from mcp_server.instance import mcp
from models.approval import Approval
from services.approval_service import create_approval


@mcp.tool()
async def create_approval_tool(approval: Approval) -> Approval:
    """
    Persist a new approval record (e.g. a pending refund request) and
    return it as stored.
    """
    return await create_approval(approval)
