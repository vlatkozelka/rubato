from abc import ABC, abstractmethod

from models.chunk import Chunk


class Chunker(ABC):
    @abstractmethod
    def chunk(self, text: str, source: str) -> list[Chunk]:
        """Split raw document text into a list of Chunk objects."""
        ...