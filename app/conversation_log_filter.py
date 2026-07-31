import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

conversation_id_var: ContextVar[Optional[str]] = ContextVar("conversation_id", default=None)


class ConversationLogFilter(logging.Filter):
    """Stamps every log record with the conversation_id currently in context."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "conversation_id"):
            record.conversation_id = conversation_id_var.get()
        return True


@contextmanager
def conversation_context(conversation_id: Optional[str]) -> Iterator[None]:
    token = conversation_id_var.set(conversation_id)
    try:
        yield
    finally:
        conversation_id_var.reset(token)
