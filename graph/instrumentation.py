import inspect
import logging
import time
from typing import Awaitable, Callable

from langchain_core.runnables import RunnableConfig

from app.timing import elapsed_ms
from models.conversation_state import ConversationState
from services.pii_redactor import PiiRedactor

logger = logging.getLogger("rubato.graph.nodes")
redactor = PiiRedactor()

NodeFn = Callable[[ConversationState], Awaitable[ConversationState]]


def instrumented_node(node_name: str, node_fn: NodeFn) -> NodeFn:
    wants_config = "config" in inspect.signature(node_fn).parameters
    async def wrapper(state: ConversationState, config: RunnableConfig) -> ConversationState:
        logger.info(
            "node_started",
            extra={
                "event": "node_started",
                "node_name": node_name,
                "input": redactor.redact_text(state.message, customer=state.customer)
            }
        )

        start = time.perf_counter()

        try:
            if wants_config:
                new_state = await node_fn(state, config)
            else:
                new_state = await node_fn(state)
        except Exception:
            logger.error(
                "node_finished",
                extra={
                    "event": "node_finished",
                    "node_name": node_name,
                    "duration_ms": elapsed_ms(start),
                    "status": "error",
                },
                exc_info=True,
            )
            raise

        customer = getattr(new_state, "customer", None)

        logger.info(
            "node_finished",
            extra={
                "event": "node_finished",
                "node_name": node_name,
                "duration_ms": elapsed_ms(start),
                "status": "ok",
                "reply": redactor.redact_text(new_state.reply, customer),
                "citations": redactor.redact_value(new_state.citations, customer),
                "triage_result": redactor.redact_value(
                    new_state.triage_result.model_dump(mode="json") if new_state.triage_result else None,
                    customer,
                ),
            },
        )
        return new_state

    wrapper.__name__ = f"instrumented_{node_name}"
    return wrapper
