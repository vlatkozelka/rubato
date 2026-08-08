import inspect
import logging
import time
from typing import Awaitable, Callable

from langchain_core.runnables import RunnableConfig
from langfuse import observe

from app.timing import elapsed_ms
from models.conversation_state import ConversationState
from services.pii_redactor import PiiRedactor

logger = logging.getLogger("rubato.graph.nodes")
redactor = PiiRedactor()

NodeFn = Callable[[ConversationState], Awaitable[ConversationState]]


def _preview(text: str | None, limit: int = 120) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"

def instrumented_node(node_name: str, node_fn: NodeFn) -> NodeFn:
    wants_config = "config" in inspect.signature(node_fn).parameters

    @observe(name=node_name, as_type="span")
    async def wrapper(state: ConversationState, config: RunnableConfig) -> ConversationState:
        log = logging.LoggerAdapter(logger, {"tag": node_name})
        input_preview = _preview(redactor.redact_text(state.message, customer=state.customer))
        log.info(f"started — input: {input_preview}")

        start = time.perf_counter()
        try:
            new_state = await (node_fn(state, config) if wants_config else node_fn(state))
        except Exception:
            log.error(f"failed after {elapsed_ms(start)}ms", exc_info=True)
            raise

        customer = getattr(new_state, "customer", None)
        reply = _preview(redactor.redact_text(new_state.reply, customer))
        intent = new_state.triage_result.intent if new_state.triage_result else None
        citations = redactor.redact_value(new_state.citations, customer) or []

        summary = f"finished in {elapsed_ms(start)}ms"
        if intent:
            summary += f" — intent={intent}"
        if reply:
            summary += f" — reply: {reply}"
        if citations:
            summary += f" — citations={citations}"
        log.info(summary)

        return new_state

    wrapper.__name__ = f"instrumented_{node_name}"
    return wrapper