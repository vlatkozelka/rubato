from pydantic import BaseModel


class Chunk(BaseModel):
    text: str
    source: str        # filename this chunk came from, e.g. "return-policy.md"
    chunk_index: int    # position within that document, 0-based
    strategy: str        # which chunker produced this, e.g. "fixed_size" or "section_aware"