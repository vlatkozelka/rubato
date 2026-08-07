import asyncio
import logging

import psycopg
from pgvector.psycopg import register_vector_async

from app.config import POSTGRES_DSN
from app.timing import log_duration
from models.chunk import Chunk
from services.embedding_service import embed_text

logger = logging.getLogger("rubato.services.retrieval")


async def _create_excerpts(query: str, top_k: int) -> str:
    chunks = await retrieve_chunks(query, top_k=top_k)

    excerpts = "\n\n".join(
        f"[{c.source}#{c.text.splitlines()[0].lstrip('# ').strip()}]\n{c.text}"
        for c in chunks
    )
    return excerpts


async def retrieve_chunks(query: str, top_k: int = 3, strategy: str = "section_aware") -> list[Chunk]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    await register_vector_async(conn)
    cur = conn.cursor()

    with log_duration(logger, "embedding_call_finished", service="embedding_service", function="embed_text"):
        query_vector = await asyncio.to_thread(embed_text, query)

    with log_duration(logger, "db_query_finished", service="retrieval_service", function="retrieve_chunks",
                      strategy=strategy, top_k=top_k):
        await cur.execute(
            """
            SELECT text, source, chunk_index, strategy
            FROM policy_chunks
            WHERE strategy = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (strategy, query_vector, top_k),
        )
        rows = await cur.fetchall()

    await cur.close()
    await conn.close()

    return [
        Chunk(text=text, source=source, chunk_index=chunk_index, strategy=strategy)
        for text, source, chunk_index, strategy in rows
    ]


async def retrieve_policy_excerpts(query: str, top_k: int = 3) -> str:
    return await _create_excerpts(query, top_k)
