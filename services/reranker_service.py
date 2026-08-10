from functools import lru_cache

from sentence_transformers import CrossEncoder

RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    return CrossEncoder(RERANKER_MODEL, device="cpu")


def rerank(query: str, candidates: list[tuple[int, str]], top_k: int) -> list[tuple[int, float]]:
    """
    candidates: list of (chunk_id, chunk_text) pairs, unordered.
    Returns (chunk_id, rerank_score) pairs sorted by reranked relevance, truncated to top_k.
    """
    if not candidates:
        return []

    model = _get_reranker()
    pairs = [[query, text] for _, text in candidates]
    scores = model.predict(pairs)

    ranked = sorted(
        zip((chunk_id for chunk_id, _ in candidates), scores),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return ranked[:top_k]