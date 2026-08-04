import logging
from typing import List

import psycopg

from app.config import POSTGRES_DSN
from models.order import Order
from models.order_item import OrderItem

logger = logging.getLogger("rubato.services.orders_by_ids")


async def get_orders_by_ids(order_ids: List[str], customer_id: str) -> List[Order]:
    if not order_ids:
        return []

    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()

    await cur.execute(
        "SELECT id, customer_id, status_kind, delivered_at, date, total "
        "FROM orders WHERE id = ANY(%s) AND customer_id = %s",
        (order_ids, customer_id),
    )
    order_rows = await cur.fetchall()

    if not order_rows:
        await cur.close()
        await conn.close()
        return []

    matched_ids = [row[0] for row in order_rows]
    await cur.execute(
        "SELECT order_id, product_id, name, qty, price, size FROM order_items "
        "WHERE order_id = ANY(%s) ORDER BY id",
        (matched_ids,),
    )
    item_rows = await cur.fetchall()
    await cur.close()
    await conn.close()

    items_by_order = {}
    for order_id, product_id, name, qty, price, size in item_rows:
        items_by_order.setdefault(order_id, []).append(
            OrderItem(product_id=product_id, name=name, qty=qty, price=float(price), size=size)
        )

    orders = []
    for id_, cust_id, status_kind, delivered_at, order_date, total in order_rows:
        orders.append(Order(
            id=id_,
            customer_id=cust_id,
            items=items_by_order.get(id_, []),
            status=status_kind,
            delivered_at=delivered_at.isoformat() if delivered_at else None,
            date=order_date.isoformat(),
            total=float(total),
        ))
    return orders
