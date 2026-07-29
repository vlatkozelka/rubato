import re

from models.chunk import Chunk
from services.chunker import Chunker


class SectionAwareChunker(Chunker):
    """
    Splits markdown text on level-2 headers ("## "), so each chunk is one
    coherent policy section, including its header. Falls back to treating
    the whole document as one chunk if no "## " headers are found.
    """

    SECTION_PATTERN = re.compile(r"(?=^## )", flags=re.MULTILINE)

    def chunk(self, text: str, source: str) -> list[Chunk]:
        # Drop the top-level "# Title" and any date/metadata line before
        # the first real section, if present.
        sections = self.SECTION_PATTERN.split(text)
        sections = [s.strip() for s in sections if s.strip().startswith("## ")]

        if not sections:
            stripped = text.strip()
            return [
                Chunk(text=stripped, source=source, chunk_index=0, strategy="section_aware")
            ] if stripped else []

        return [
            Chunk(text=section, source=source, chunk_index=i, strategy="section_aware")
            for i, section in enumerate(sections)
        ]