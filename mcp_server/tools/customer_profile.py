from typing import Optional

from mcp_server.instance import mcp
from models.customer_account import CustomerAccount
from services.customer_account_service import get_customer_account


@mcp.tool()
async def get_customer_profile_tool(customer_id: str) -> Optional[CustomerAccount]:
    """
    Look up a customer's own profile: email, tier, and refund request
    count. Returns None if no customer with that ID exists.
    """
    return await get_customer_account(customer_id)
