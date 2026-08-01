import logging
from typing import List, Optional

import psycopg

from app.config import POSTGRES_DSN
from models.product import Product

logger = logging.getLogger("rubato.services.product")

_COLUMNS = "id, name, price, category, size, stock"


def _row_to_product(row) -> Product:
    id_, name, price, category, size, stock = row
    return Product(id=id_, name=name, price=float(price), category=category, size=size, stock=stock)


def list_products() -> List[Product]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(f"SELECT {_COLUMNS} FROM products ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_row_to_product(r) for r in rows]


def update_product(product_id: str, fields: dict) -> Optional[Product]:
    """fields keys are trusted column names from ProductUpdate (see routers/products.py),
    never raw user input, so building the SET clause from them is safe."""
    if not fields:
        return get_product_by_id(product_id)

    set_clause = ", ".join(f"{column} = %s" for column in fields)
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE products SET {set_clause} WHERE id = %s RETURNING {_COLUMNS}",
        (*fields.values(), product_id),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return _row_to_product(row) if row else None


def get_product_by_id(product_id: str) -> Optional[Product]:
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()
    cur.execute(f"SELECT {_COLUMNS} FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _row_to_product(row) if row else None


def get_products_by_name(name: str, limit: int = 20) -> List[Product]:
    """
    Full-text search over name (weight A) + category (weight B), ranked with
    ts_rank_cd. Falls back to pg_trgm word_similarity for typo tolerance
    (e.g. "sweter" -> "Sweater") when full-text search finds nothing — see
    DECISIONS.md for why this supersedes the old word-overlap matcher.
    """
    conn = psycopg.connect(POSTGRES_DSN)
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT {_COLUMNS}
        FROM products
        WHERE search_vector @@ websearch_to_tsquery('english', %s)
        ORDER BY ts_rank_cd(search_vector, websearch_to_tsquery('english', %s)) DESC
        LIMIT %s
        """,
        (name, name, limit),
    )
    rows = cur.fetchall()

    if not rows:
        # word_similarity (not similarity/`%`) because the query is usually a
        # short product reference ("sweter") matched against a longer,
        # multi-word product name ("Northline Merino Sweater") — plain
        # whole-string similarity scores those too low to be useful.
        # Filtering in Python-land SQL rather than via the `<%` operator
        # (default threshold 0.6) keeps the threshold explicit; at catalog
        # sizes beyond a sandbox, switch to `<%` with
        # `SET pg_trgm.word_similarity_threshold` so the trigram GIN index
        # is used instead of a sequential scan.
        cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM products
            WHERE word_similarity(%s, name) > 0.3
            ORDER BY word_similarity(%s, name) DESC
            LIMIT %s
            """,
            (name, name, limit),
        )
        rows = cur.fetchall()

    cur.close()
    conn.close()
    return [_row_to_product(r) for r in rows]
