import logging
from typing import Optional

from models.order import Order
from models.order_item import OrderItem
from services.order_service import get_order_by_id

logger = logging.getLogger("rubato.services.return_service")


def initiate_return(order_id: str, product_id: str, customer_id: str, reason: str) -> Optional[OrderItem]:
    logger.info(
        "initiate_return_called",
        extra={"event": "initiate_return_called", "order_id": order_id, "customer_id": customer_id},
    )
    order: Optional[Order] = get_order_by_id(order_id)
    if order is None or order.customer_id != customer_id:
        return None

    for item in order.items:
        if item.product_id == product_id:
            logger.info(
                "return_initiated",
                extra={"event": "return_initiated", "order_id": order_id, "product_id": product_id, "reason": reason},
            )
            return item

    return None
