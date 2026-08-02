from mcp_server.instance import mcp
from services.product_service import get_products_by_name
from models.product import Product


@mcp.tool()
async def get_products_by_name_tool(name: str, limit: int = 20) -> list[Product]:
    """
    Search products by name/category using full-text search, with a
    trigram-similarity fallback for typo tolerance when full-text search
    finds no matches. Returns up to `limit` matching products, ranked by
    relevance.
    """
    return await get_products_by_name(name, limit)