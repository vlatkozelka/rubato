import logging
import time
from typing import Awaitable, Callable

from app.timing import elapsed_ms
from models.conversation_state import ConversationState

logger = logging.getLogger("rubato.graph.nodes")

NodeFn = Callable[[ConversationState], Awaitable[ConversationState]]


def instrumented_node(node_name: str, node_fn: NodeFn) -> NodeFn:
    """Wrap a node function with entry/exit/timing/error logging.

    Applied when nodes are registered on the StateGraph, so node functions
    in graph/simple_nodes.py stay free of logging concerns. Reused for every node —
    new nodes get this instrumentation for free by wrapping them the same way.
    """

    async def wrapper(state: ConversationState) -> ConversationState:
        logger.info("node_started", extra={"event": "node_started", "node_name": node_name})

        results_before = len(state.results)
        triage_before = state.triage_result.model_dump(mode="json") if state.triage_result else None
        start = time.perf_counter()

        try:
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

        triage_after = new_state.triage_result.model_dump(mode="json") if new_state.triage_result else None
        logger.info(
            "node_finished",
            extra={
                "event": "node_finished",
                "node_name": node_name,
                "duration_ms": elapsed_ms(start),
                "status": "ok",
                "results_produced": [r.model_dump(mode="json") for r in new_state.results[results_before:]],
                "triage_result": triage_after if triage_after != triage_before else None,
            },
        )
        return new_state

    wrapper.__name__ = f"instrumented_{node_name}"
    return wrapper
