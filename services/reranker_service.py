import voyageai

RERANKER_MODEL = "rerank-2.5"

_rerank_client = voyageai.AsyncClient()


async def rerank(query: str, candidates: list[tuple[int, str]], top_k: int) -> list[tuple[int, float]]:
    """
    candidates: list of (chunk_id, chunk_text) pairs, unordered.
    Returns (chunk_id, rerank_score) pairs sorted by reranked relevance, truncated to top_k.
    """
    if not candidates:
        return []

    documents = [text for _, text in candidates]
    result = await _rerank_client.rerank(query, documents, model=RERANKER_MODEL, top_k=top_k)

    return [(candidates[r.index][0], r.relevance_score) for r in result.results]