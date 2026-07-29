import psycopg
from pgvector.psycopg import register_vector

from app.config import POSTGRES_DSN
from models.chunk import Chunk
from services.embedding_service import embed_text


def retrieve_chunks(query: str, top_k: int = 3, strategy: str = "section_aware") -> list[Chunk]:
    conn = psycopg.connect(POSTGRES_DSN)
    register_vector(conn)
    cur = conn.cursor()

    query_vector = embed_text(query)

    cur.execute(
        """
        SELECT text, source, chunk_index, strategy
        FROM policy_chunks
        WHERE strategy = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (strategy, query_vector, top_k),
    )
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        Chunk(text=text, source=source, chunk_index=chunk_index, strategy=strategy)
        for text, source, chunk_index, strategy in rows
    ]