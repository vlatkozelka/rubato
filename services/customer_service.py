import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from models.customer import Customer

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
