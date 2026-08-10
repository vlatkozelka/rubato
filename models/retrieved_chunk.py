from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    chunk_id: int
    source_doc: str          # e.g. "return-policy.md" — you already need this for citations
    text: str
    rank: int                # final position after rerank
    rrf_score: float         # fusion score, pre-rerank
    rerank_score: float      # cross-encoder score, post-rerank