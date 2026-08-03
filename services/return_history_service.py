import logging
from typing import List

import psycopg

from app.config import POSTGRES_DSN
from models.return_history import ReturnHistoryEntry

logger = logging.getLogger("rubato.services.return_history")

_COLUMNS = "id, customer_id, order_id, product_id, reason, requested_at, resolution, amount"


def _row_to_entry(row) -> ReturnHistoryEntry:
    id_, customer_id, order_id, product_id, reason, requested_at, resolution, amount = row
    return ReturnHistoryEntry(
        id=id_,
        customer_id=customer_id,
        order_id=order_id,
        product_id=product_id,
        reason=reason,
        requested_at=requested_at.isoformat(),
        resolution=resolution,
        amount=float(amount),
    )


async def get_return_history(customer_id: str) -> List[ReturnHistoryEntry]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        f"SELECT {_COLUMNS} FROM return_history WHERE customer_id = %s ORDER BY requested_at DESC",
        (customer_id,),
    )
    rows = await cur.fetchall()
    await cur.close()
    await conn.close()
    return [_row_to_entry(r) for r in rows]
