import logging
from datetime import datetime, timezone
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from models.customer import Customer
from models.customer_profile import CustomerProfile

logger = logging.getLogger("rubato.services.customer")


def get_customer_by_id(customer_id: str) -> Optional[Customer]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email, tier FROM customers WHERE id = %s",
        (customer_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    id_, name, email, tier = row
    return Customer(id=id_, name=name, email=email, tier=tier)


async def get_customer_profile(customer_id: str) -> Optional[CustomerProfile]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()

    await cur.execute(
        "SELECT customer_id, refund_request_count, last_contacted_at, notes "
        "FROM customer_profiles WHERE customer_id = %s",
        (customer_id,),
    )
    row = await cur.fetchone()
    await cur.close()
    await conn.close()

    if row is None:
        return None

    customer_id_, refund_count, last_contacted, notes = row
    return CustomerProfile(
        customer_id=customer_id_,
        refund_request_count=refund_count,
        last_contacted_at=last_contacted,
        notes=notes,
    )


async def update_last_contacted(customer_id: str) -> None:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        "UPDATE customer_profiles SET last_contacted_at = %s WHERE customer_id = %s",
        (datetime.now(timezone.utc), customer_id),
    )
    await conn.commit()
    await cur.close()
    await conn.close()


async def increment_refund_request_count(customer_id: str) -> None:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    cur = conn.cursor()
    await cur.execute(
        "UPDATE customer_profiles SET refund_request_count = refund_request_count + 1 "
        "WHERE customer_id = %s",
        (customer_id,),
    )
    await conn.commit()
    await cur.close()
    await conn.close()
