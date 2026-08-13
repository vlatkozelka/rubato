import voyageai

_voyage_ai_client = voyageai.Client()

VOYAGE_EMBEDDING_MODEL="voyage-4-large"
VOYAGE_EMBEDDING_DIM=1024


async def embed_documents(texts: list[str]) -> list[list[float]]:
    result = _voyage_ai_client.embed(
        texts,
        model=VOYAGE_EMBEDDING_MODEL,
        input_type="document",
        output_dimension=VOYAGE_EMBEDDING_DIM,
    )
    return result.embeddings


async def embed_query(text: str) -> list[float]:
    result = _voyage_ai_client.embed(
        [text],
        model=VOYAGE_EMBEDDING_MODEL,
        input_type="query",
        output_dimension=VOYAGE_EMBEDDING_DIM,
    )
    return result.embeddings[0]
