from typing import Optional
from uuid import UUID

from mcp_server.instance import mcp
from models.approval import Approval
from services.approval_service import get_approval_by_id


@mcp.tool()
async def get_approval_status_tool(approval_id: UUID, customer_id: str) -> Optional[Approval]:
    """
    Look up the current status (pending review, approved, or denied) of a
    previously created approval by its ID. Returns None if no approval
    with that ID exists for the given customer.
    """
    return await get_approval_by_id(approval_id, customer_id)
