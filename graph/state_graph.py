import asyncio
import logging

from langgraph.constants import END
from langgraph.graph import StateGraph

from graph.instrumentation import instrumented_node
from graph.nodes import triage_node, check_order_status_node, check_price_node, answer_policy_question_node, greet_node, \
    composite_node, refund_request_node, return_request_node
from models.conversation_state import ConversationState
from models.intent import Intent
from models.node_id import NodeId

logger = logging.getLogger("rubato.graph.router")

graph = StateGraph(ConversationState)
graph.add_node(NodeId.TRIAGE, instrumented_node(NodeId.TRIAGE.value, triage_node))
graph.add_node(NodeId.CHECK_ORDER_STATUS, instrumented_node(NodeId.CHECK_ORDER_STATUS.value, check_order_status_node))
graph.add_node(NodeId.CHECK_PRICE, instrumented_node(NodeId.CHECK_PRICE.value, check_price_node))
graph.add_node(NodeId.ANSWER_POLICY_QUESTION,
               instrumented_node(NodeId.ANSWER_POLICY_QUESTION.value, answer_policy_question_node))
graph.add_node(NodeId.GREET, instrumented_node(NodeId.GREET.value, greet_node))
graph.add_node(NodeId.HANDLE_COMPOSITE, instrumented_node(NodeId.HANDLE_COMPOSITE.value, composite_node))
graph.add_node(NodeId.HANDLE_REFUND_REQUEST, instrumented_node(NodeId.HANDLE_REFUND_REQUEST.value, refund_request_node))
graph.add_node(NodeId.HANDLE_RETURN_REQUEST, instrumented_node(NodeId.HANDLE_RETURN_REQUEST.value, return_request_node))
graph.set_entry_point(NodeId.TRIAGE)


def traverse(state: ConversationState) -> str:
    if state.triage_result is None:
        logger.error(
            "router_failed",
            extra={"event": "router_failed", "reason": "triage_result is None"},
        )
        raise ValueError("traverse called with triage_result = None")
    else:
        intent = state.triage_result.intent

        match intent:
            case Intent.ORDER_STATUS:
                target_node = NodeId.CHECK_ORDER_STATUS
            case Intent.POLICY_QUESTION:
                target_node = NodeId.ANSWER_POLICY_QUESTION
            case Intent.RETURN_REQUEST:
                target_node = NodeId.HANDLE_RETURN_REQUEST
            case Intent.REFUND_REQUEST:
                target_node = NodeId.HANDLE_REFUND_REQUEST
            case Intent.PRICE_CHECK:
                target_node = NodeId.CHECK_PRICE
            case Intent.ESCALATE:
                target_node = NodeId.ASSIGN_TO_HUMAN
            case Intent.CHITCHAT:
                target_node = NodeId.GREET
            case Intent.COMPOSITE:
                target_node = NodeId.HANDLE_COMPOSITE
            case Intent.COMPLEX_CASE:
                target_node = NodeId.PROCESS_COMPLEX_CASE
            case _:
                target_node = None

        logger.info(
            "router_decision",
            extra={
                "event": "router_decision",
                "intent": intent.value,
                "target_node": target_node.value if target_node else None,
            },
        )
        return target_node


path_map = {
    NodeId.CHECK_ORDER_STATUS: NodeId.CHECK_ORDER_STATUS,
    NodeId.CHECK_PRICE: NodeId.CHECK_PRICE,
    NodeId.ANSWER_POLICY_QUESTION: NodeId.ANSWER_POLICY_QUESTION,
    NodeId.GREET: NodeId.GREET,
    NodeId.HANDLE_COMPOSITE: NodeId.HANDLE_COMPOSITE,
    NodeId.HANDLE_RETURN_REQUEST: NodeId.HANDLE_RETURN_REQUEST,
    NodeId.HANDLE_REFUND_REQUEST: NodeId.HANDLE_REFUND_REQUEST,
    # everything else routes to END until those nodes exist
    NodeId.ASSIGN_TO_HUMAN: END,
    NodeId.PROCESS_COMPLEX_CASE: END,
}
graph.add_conditional_edges(
    NodeId.TRIAGE,
    traverse,
    path_map,
)

graph.add_edge(NodeId.CHECK_ORDER_STATUS, END)
graph.add_edge(NodeId.CHECK_PRICE, END)
graph.add_edge(NodeId.ANSWER_POLICY_QUESTION, END)
graph.add_edge(NodeId.GREET, END)
graph.add_edge(NodeId.HANDLE_REFUND_REQUEST, END)
graph.add_edge(NodeId.HANDLE_RETURN_REQUEST, END)
graph.add_conditional_edges(NodeId.HANDLE_COMPOSITE, traverse, path_map)

app_graph = graph.compile()


async def _main() -> None:
    messages = [
        "Can I return software products?",
        "What are the prices of jackets?"
    ]

    i = 0

    for message in messages:
        result = await app_graph.ainvoke(ConversationState(
            id=f"test-{i}",
            message=message,
        ))
        i = i + 1


if __name__ == "__main__":
    from app.logging_setup import configure_logging

    configure_logging()

    asyncio.run(_main())
