import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from models.customer_account import CustomerAccount

logger = logging.getLogger("rubato.services.customer_account")


async def get_customer_account(customer_id: str) -> Optional[CustomerAccount]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        """
        SELECT c.id, c.email, c.tier, COALESCE(p.refund_request_count, 0), p.last_contacted_at
        FROM customers c
        LEFT JOIN customer_profiles p ON p.customer_id = c.id
        WHERE c.id = %s
        """,
        (customer_id,),
    )
    row = await cur.fetchone()
    await cur.close()
    await conn.close()

    if row is None:
        return None

    id_, email, tier, refund_count, last_contacted = row
    return CustomerAccount(
        id=id_,
        email=email,
        tier=tier,
        refund_request_count=refund_count,
        last_contacted_at=last_contacted,
    )
