from langgraph.constants import END
from langgraph.graph import StateGraph

from graph.nodes import triage_node, check_order_status_node, check_price_node, answer_policy_question_node, greet_node, \
    composite_node
from models.conversation_state import ConversationState
from models.intent import Intent
from models.node_id import NodeId

graph = StateGraph(ConversationState)
graph.add_node(NodeId.TRIAGE, triage_node)
graph.add_node(NodeId.CHECK_ORDER_STATUS, check_order_status_node)
graph.add_node(NodeId.CHECK_PRICE, check_price_node)
graph.add_node(NodeId.ANSWER_POLICY_QUESTION, answer_policy_question_node)
graph.add_node(NodeId.GREET, greet_node)
graph.add_node(NodeId.HANDLE_COMPOSITE, composite_node)
graph.set_entry_point(NodeId.TRIAGE)


def traverse(state: ConversationState) -> str:
    if state.triage_result is None:
        raise ValueError("traverse called with triage_result = None")
    else:
        match state.triage_result.intent:

            case Intent.ORDER_STATUS:
                return NodeId.CHECK_ORDER_STATUS
            case Intent.POLICY_QUESTION:
                return NodeId.ANSWER_POLICY_QUESTION
            case Intent.RETURN_REQUEST:
                return NodeId.HANDLE_RETURN_REQUEST
            case Intent.REFUND_REQUEST:
                return NodeId.HANDLE_REFUND_REQUEST
            case Intent.PRICE_CHECK:
                return NodeId.CHECK_PRICE
            case Intent.ESCALATE:
                return NodeId.ASSIGN_TO_HUMAN
            case Intent.CHITCHAT:
                return NodeId.GREET
            case Intent.COMPOSITE:
                return NodeId.HANDLE_COMPOSITE
            case Intent.COMPLEX_CASE:
                return NodeId.PROCESS_COMPLEX_CASE


path_map = {
    NodeId.CHECK_ORDER_STATUS: NodeId.CHECK_ORDER_STATUS,
    NodeId.CHECK_PRICE: NodeId.CHECK_PRICE,
    NodeId.ANSWER_POLICY_QUESTION: NodeId.ANSWER_POLICY_QUESTION,
    NodeId.GREET: NodeId.GREET,
    NodeId.HANDLE_COMPOSITE: NodeId.HANDLE_COMPOSITE,
    # everything else routes to END until those nodes exist
    NodeId.HANDLE_RETURN_REQUEST: END,
    NodeId.HANDLE_REFUND_REQUEST: END,
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
graph.add_conditional_edges(NodeId.HANDLE_COMPOSITE, traverse, path_map)

app_graph = graph.compile()


if __name__ == "__main__":
    messages = [
        "I want to know the prices of jackets, and I want to return a game I bought"
    ]

    i = 0

    for message in messages:
        result = app_graph.invoke(ConversationState(
            id=f"test-{i}",
            message=message,
        ))

        print(result)
        i = i + 1
