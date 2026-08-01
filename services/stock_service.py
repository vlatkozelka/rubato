import logging
from typing import Optional

import psycopg

from app.config import POSTGRES_DSN

logger = logging.getLogger("rubato.services.stock")


def check_stock(product_id: str) -> Optional[int]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute("SELECT stock FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None
