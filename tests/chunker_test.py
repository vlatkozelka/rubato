from pathlib import Path

from app.config import DOCS_DIR
from services.fixed_size_chunker import FixedSizeChunker
from services.section_aware_chunker import SectionAwareChunker

text = Path(DOCS_DIR / "return-policy.md").read_text(encoding="utf-8")

for chunker in [FixedSizeChunker(), SectionAwareChunker()]:
    print(f"--- {chunker.__class__.__name__} ---")
    chunks = chunker.chunk(text, source="return-policy.md")
    for c in chunks:
        print(f"[{c.chunk_index}] ({len(c.text)} chars) {c.text[:80]}...")
    print()