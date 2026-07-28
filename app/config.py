"""
Central config, read from environment variables so behavior differs cleanly
between local dev, docker-compose, and (later) a cloud model swap.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

# LM Studio exposes an OpenAI-compatible /v1 endpoint. Default assumes LM
# Studio is running on the host machine, reachable from inside a container
# via host.docker.internal. Override via env when running bare-metal.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")  # LM Studio ignores the value but the SDK requires one
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-14b-instruct")

# Reserved for Phase 5+ model routing: a second, larger model for the
# complex-case agent loop, potentially a cloud model behind the same
# OpenAI-compatible interface.
LLM_MODEL_COMPLEX = os.getenv("LLM_MODEL_COMPLEX", LLM_MODEL)

# Reserved for Phase 4+.
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN", "postgresql://rubato:rubato@localhost:5432/rubato"
)

# Reserved for Phase 11.
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
