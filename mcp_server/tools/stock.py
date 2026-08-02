from mcp_server.instance import mcp
from services.stock_service import check_stock


@mcp.tool()
def check_stock_tool(product_id: str) -> int | None:
    """
    Look up current stock quantity for a product by its ID.
    Returns the stock count, or None if the product ID doesn't exist.
    """
    return check_stock(product_id)