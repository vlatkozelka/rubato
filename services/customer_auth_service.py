import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN
from app.security import verify_password
from models.customer import Customer

logger = logging.getLogger("rubato.services.customer_auth")


def authenticate_customer(email: str, password: str) -> Optional[Customer]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email, password_hash, tier FROM customers WHERE email = %s",
        (email,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    id_, name, customer_email, password_hash, tier = row
    if not verify_password(password, password_hash):
        return None

    return Customer(id=id_, name=name, email=customer_email, tier=tier)
