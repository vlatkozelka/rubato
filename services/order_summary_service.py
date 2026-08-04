import logging
from typing import List, Optional

import psycopg

from app.config import POSTGRES_DSN
from models.order_summary import OrderSummary

logger = logging.getLogger("rubato.services.order_summary")


async def get_orders_by_customer(customer_id: str, limit: int = 5, status: Optional[str] = None) -> List[OrderSummary]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()

    if status is not None:
        await cur.execute(
            "SELECT id, date, status_kind, total FROM orders "
            "WHERE customer_id = %s AND status_kind = %s "
            "ORDER BY date DESC LIMIT %s",
            (customer_id, status, limit),
        )
    else:
        await cur.execute(
            "SELECT id, date, status_kind, total FROM orders "
            "WHERE customer_id = %s "
            "ORDER BY date DESC LIMIT %s",
            (customer_id, limit),
        )
    order_rows = await cur.fetchall()

    summaries = []
    for order_id, order_date, status_kind, total in order_rows:
        await cur.execute(
            "SELECT name FROM order_items WHERE order_id = %s ORDER BY id",
            (order_id,),
        )
        item_rows = await cur.fetchall()
        summaries.append(OrderSummary(
            order_id=order_id,
            placed_at=order_date.isoformat(),
            status=status_kind,
            total=float(total),
            item_names=[name for (name,) in item_rows],
        ))

    await cur.close()
    await conn.close()
    return summaries
