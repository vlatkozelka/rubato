from models.chunk import Chunk
from services.chunker import Chunker


class FixedSizeChunker(Chunker):
    """
    Splits text into ~chunk_size-character windows with overlap between
    consecutive chunks. Snaps to word boundaries (never cuts mid-word) but
    has no awareness of document structure — a chunk can start or end
    anywhere relative to a paragraph or section.
    """

    def __init__(self, chunk_size: int = 800, overlap: int = 100):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, source: str) -> list[Chunk]:
        words = text.split()
        chunks: list[Chunk] = []
        start = 0
        index = 0

        while start < len(words):
            piece = []
            length = 0
            i = start
            while i < len(words) and length < self.chunk_size:
                piece.append(words[i])
                length += len(words[i]) + 1  # +1 for the space
                i += 1

            chunk_text = " ".join(piece)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    source=source,
                    chunk_index=index,
                    strategy="fixed_size",
                )
            )
            index += 1

            if i >= len(words):
                break

            # step back by roughly `overlap` characters worth of words
            overlap_words = 0
            overlap_len = 0
            j = i - 1
            while j > start and overlap_len < self.overlap:
                overlap_len += len(words[j]) + 1
                overlap_words += 1
                j -= 1

            start = i - overlap_words

        return chunks