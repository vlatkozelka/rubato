import logging

from app.config import LOG_LEVEL
from app.conversation_log_filter import ConversationLogFilter
from app.json_log_formatter import JsonLogFormatter

_configured = False


def configure_logging() -> None:
    """Wire up stdlib logging to emit single-line JSON records.

    Scoped to the "rubato" logger tree (not root) so it doesn't clash with
    uvicorn's own logging config. Idempotent — safe to call from multiple
    entry points (FastAPI app startup, standalone scripts).
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(ConversationLogFilter())

    rubato_logger = logging.getLogger("rubato")
    rubato_logger.handlers = [handler]
    rubato_logger.setLevel(level)
    rubato_logger.propagate = False

    _configured = True
