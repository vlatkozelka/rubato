import asyncio
import logging
from typing import List

import psycopg
from pgvector.psycopg import register_vector_async

from app.config import POSTGRES_DSN
from app.timing import log_duration
from models.retrieved_chunk import RetrievedChunk
from services.embedding_service import embed_query
from services.reranker_service import rerank

logger = logging.getLogger("rubato.services.retrieval")

RRF_K = 60
CANDIDATE_K = 20




async def _vector_candidates(cur, query_vector, strategy: str, candidate_k: int):
    await cur.execute(
        """
        SELECT id, text, source, chunk_index, strategy
        FROM policy_chunks
        WHERE strategy = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (strategy, query_vector, candidate_k),
    )
    return await cur.fetchall()


async def _fulltext_candidates(cur, query: str, strategy: str, candidate_k: int):
    await cur.execute(
        """
        SELECT id, text, source, chunk_index, strategy
        FROM policy_chunks
        WHERE strategy = %s AND text_search @@ plainto_tsquery('simple', %s)
        ORDER BY ts_rank(text_search, plainto_tsquery('simple', %s)) DESC
        LIMIT %s
        """,
        (strategy, query, query, candidate_k),
    )
    return await cur.fetchall()


def _reciprocal_rank_fusion(*ranked_lists: list[tuple], k: int = RRF_K) -> dict[int, tuple[float, tuple]]:
    """
    Each ranked_list is a list of rows (id, text, source, chunk_index, strategy),
    already ordered best-first. Returns {chunk_id: (fused_score, row)}.
    """
    fused: dict[int, float] = {}
    rows_by_id: dict[int, tuple] = {}

    for ranked_list in ranked_lists:
        for rank, row in enumerate(ranked_list):
            chunk_id = row[0]
            rows_by_id[chunk_id] = row
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    return {chunk_id: (score, rows_by_id[chunk_id]) for chunk_id, score in fused.items()}


async def retrieve_chunks(query: str, top_k: int = 5, strategy: str = "section_aware") -> list[RetrievedChunk]:
    conn = await psycopg.AsyncConnection.connect(POSTGRES_DSN)
    await register_vector_async(conn)
    cur = conn.cursor()

    with log_duration(logger, "embedding_call_finished", service="embedding_service", function="embed_query"):
        query_vector = await embed_query(query)

    with log_duration(logger, "db_query_finished", service="retrieval_service", function="retrieve_chunks",
                      strategy=strategy, candidate_k=CANDIDATE_K):
        vector_rows = await _vector_candidates(cur, query_vector, strategy, CANDIDATE_K)
        fulltext_rows = await _fulltext_candidates(cur, query, strategy, CANDIDATE_K)

    await cur.close()
    await conn.close()

    fused = _reciprocal_rank_fusion(vector_rows, fulltext_rows)
    if not fused:
        return []

    candidates = [(chunk_id, row[1]) for chunk_id, (_, row) in fused.items()]

    with log_duration(logger, "rerank_finished", service="reranker_service", function="rerank",
                      candidate_count=len(candidates)):
        reranked = await rerank(query, candidates, top_k)  # list[(chunk_id, rerank_score)]

    rrf_scores = {chunk_id: score for chunk_id, (score, _) in fused.items()}
    rows_by_id = {chunk_id: row for chunk_id, (_, row) in fused.items()}

    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            source_doc=rows_by_id[chunk_id][2],
            text=rows_by_id[chunk_id][1],
            rank=rank,
            rrf_score=rrf_scores[chunk_id],
            rerank_score=rerank_score,
        )
        for rank, (chunk_id, rerank_score) in enumerate(reranked, start=1)
    ]


async def retrieve_policy_excerpts(query: str, top_k: int = 5) -> List[RetrievedChunk]:
    return await retrieve_chunks(query, top_k)


def create_excerpts_from_chunks(chunks: List[RetrievedChunk]) -> str:
    excerpts = "\n\n".join(
        f"[{chunk.source_doc}#{chunk.text.splitlines()[0].lstrip('# ').strip()}]\n{chunk.text}"
        for chunk in chunks
    )
    return excerpts