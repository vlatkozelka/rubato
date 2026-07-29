# services/embedding_service.py
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("BAAI/bge-m3")


def embed_text(text: str) -> list[float]:
    return _model.encode(text, normalize_embeddings=True).tolist()