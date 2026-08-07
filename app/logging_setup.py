import logging

from app.config import LOG_LEVEL
from app.conversation_log_filter import ConversationLogFilter
from app.json_log_formatter import JsonLogFormatter

_configured = False

import logging

class LogcatFormatter(logging.Formatter):
    """timestamp \t tag \t level \t message — Android logcat style."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        tag = getattr(record, "tag", record.name)
        return f"{timestamp}\t{tag}\t{record.levelname}\t{record.getMessage()}"


def configure_logcat_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(LogcatFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def configure_logging() -> None:
    """Wire up stdlib logging to emit logcat style log records.

    Scoped to the "rubato" logger tree (not root) so it doesn't clash with
    uvicorn's own logging config. Idempotent — safe to call from multiple
    entry points (FastAPI app startup, standalone scripts).
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(LogcatFormatter())
    handler.addFilter(ConversationLogFilter())

    rubato_logger = logging.getLogger("rubato")
    rubato_logger.handlers = [handler]
    rubato_logger.setLevel(level)
    rubato_logger.propagate = False

    _configured = True
