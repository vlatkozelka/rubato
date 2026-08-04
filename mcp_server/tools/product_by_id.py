from typing import Optional

from mcp_server.instance import mcp
from models.product import Product
from services.product_service import get_product_by_id


@mcp.tool()
async def get_product_by_id_tool(product_id: str) -> Optional[Product]:
    """
    Look up a product by its exact ID, returning its full record (name,
    price, category, size, stock). Returns None if no product with that
    ID exists.
    """
    return await get_product_by_id(product_id)
