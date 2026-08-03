from mcp_server.instance import mcp
from models.return_history import ReturnHistoryEntry
from services.return_history_service import get_return_history


@mcp.tool()
async def get_return_history_tool(customer_id: str) -> list[ReturnHistoryEntry]:
    """
    Look up a customer's return history by customer ID, most recent first.
    Returns an empty list if the customer has no returns on record.
    """
    return await get_return_history(customer_id)
