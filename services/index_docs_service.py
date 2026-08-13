import asyncio

import psycopg
from pgvector.psycopg import register_vector

from app.config import DOCS_DIR, POSTGRES_DSN
from services.chunker import Chunker
from services.embedding_service import embed_documents, VOYAGE_EMBEDDING_MODEL
from services.section_aware_chunker import SectionAwareChunker


async def index_docs(chunker: Chunker) -> None:
    conn = psycopg.connect(POSTGRES_DSN)
    register_vector(conn)
    cur = conn.cursor()

    for doc_path in DOCS_DIR.glob("*.md"):
        text = doc_path.read_text(encoding="utf-8")
        chunks = chunker.chunk(text, source=doc_path.name)
        if not chunks:
            continue

        vectors = await embed_documents([c.text for c in chunks])

        for c, vector in zip(chunks, vectors):
            cur.execute(
                """
                INSERT INTO policy_chunks
                    (text, source, chunk_index, strategy, embedding_model, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (c.text, c.source, c.chunk_index, c.strategy, VOYAGE_EMBEDDING_MODEL, vector),
            )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    #index_docs(FixedSizeChunker())
    asyncio.run(index_docs(SectionAwareChunker()))