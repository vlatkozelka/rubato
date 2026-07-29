import psycopg
from pgvector.psycopg import register_vector

from app.config import DOCS_DIR, POSTGRES_DSN
from services.embedding_service import embed_text
from services.chunker import Chunker
from services.fixed_size_chunker import FixedSizeChunker
from services.section_aware_chunker import SectionAwareChunker


def index_docs(chunker: Chunker) -> None:
    conn = psycopg.connect(POSTGRES_DSN)
    register_vector(conn)
    cur = conn.cursor()

    for doc_path in DOCS_DIR.glob("*.md"):
        text = doc_path.read_text(encoding="utf-8")
        chunks = chunker.chunk(text, source=doc_path.name)

        for c in chunks:
            vector = embed_text(c.text)
            cur.execute(
                """
                INSERT INTO policy_chunks (text, source, chunk_index, strategy, embedding)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (c.text, c.source, c.chunk_index, c.strategy, vector),
            )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    #index_docs(FixedSizeChunker())
    index_docs(SectionAwareChunker())