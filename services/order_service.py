import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from models.order import Order
from models.order_item import OrderItem

logger = logging.getLogger("rubato.services.order")


def get_order_by_id(order_id: str) -> Optional[Order]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, customer_id, status_kind, delivered_at, date, total FROM orders WHERE id = %s",
        (order_id,),
    )
    order_row = cur.fetchone()
    if order_row is None:
        cur.close()
        conn.close()
        return None

    cur.execute(
        "SELECT product_id, name, qty, price, size FROM order_items WHERE order_id = %s ORDER BY id",
        (order_id,),
    )
    item_rows = cur.fetchall()
    cur.close()
    conn.close()

    id_, customer_id, status_kind, delivered_at, order_date, total = order_row
    items = [
        OrderItem(product_id=product_id, name=name, qty=qty, price=float(price), size=size)
        for product_id, name, qty, price, size in item_rows
    ]

    # Order's model_validator expects the flat shape orders.json used
    # ("status" + a top-level "delivered_at"), so it can stay unchanged.
    return Order(
        id=id_,
        customer_id=customer_id,
        items=items,
        status=status_kind,
        delivered_at=delivered_at.isoformat() if delivered_at else None,
        date=order_date.isoformat(),
        total=float(total),
    )
