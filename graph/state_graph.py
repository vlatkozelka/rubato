from langgraph.constants import END
from langgraph.graph import StateGraph

from graph.nodes import triage_node, check_order_status_node, check_price_node, answer_policy_question_node, greet_node, \
    composite_node
from models.conversation_state import ConversationState
from models.intent import Intent
from models.node_id import NodeId

graph = StateGraph(ConversationState)
graph.add_node(NodeId.TRIAGE.value, triage_node)
graph.add_node(NodeId.CHECK_ORDER_STATUS.value, check_order_status_node)
graph.add_node(NodeId.CHECK_PRICE.value, check_price_node)
graph.add_node(NodeId.ANSWER_POLICY_QUESTION.value, answer_policy_question_node)
graph.add_node(NodeId.GREET.value, greet_node)
graph.add_node(NodeId.HANDLE_COMPOSITE.value, composite_node)
graph.set_entry_point(NodeId.TRIAGE.value)


def traverse(state: ConversationState) -> str:
    if state.triage_result is None:
        raise ValueError("traverse called with triage_result = None")
    else:
        match state.triage_result.intent:

            case Intent.ORDER_STATUS:
                return NodeId.CHECK_ORDER_STATUS.value
            case Intent.POLICY_QUESTION:
                return NodeId.ANSWER_POLICY_QUESTION.value
            case Intent.RETURN_REQUEST:
                return NodeId.HANDLE_RETURN_REQUEST.value
            case Intent.REFUND_REQUEST:
                return NodeId.HANDLE_REFUND_REQUEST.value
            case Intent.PRICE_CHECK:
                return NodeId.CHECK_PRICE.value
            case Intent.ESCALATE:
                return NodeId.ASSIGN_TO_HUMAN.value
            case Intent.CHITCHAT:
                return NodeId.GREET.value
            case Intent.COMPOSITE:
                return NodeId.HANDLE_COMPOSITE.value
            case Intent.COMPLEX_CASE:
                return NodeId.PROCESS_COMPLEX_CASE.value


path_map = {
    NodeId.CHECK_ORDER_STATUS.value: NodeId.CHECK_ORDER_STATUS.value,
    NodeId.CHECK_PRICE.value: NodeId.CHECK_PRICE.value,
    NodeId.ANSWER_POLICY_QUESTION.value: NodeId.ANSWER_POLICY_QUESTION.value,
    NodeId.GREET.value: NodeId.GREET.value,
    NodeId.HANDLE_COMPOSITE.value: NodeId.HANDLE_COMPOSITE.value,
    # everything else routes to END until those nodes exist
    NodeId.HANDLE_RETURN_REQUEST.value: END,
    NodeId.HANDLE_REFUND_REQUEST.value: END,
    NodeId.ASSIGN_TO_HUMAN.value: END,
    NodeId.PROCESS_COMPLEX_CASE.value: END,
}
graph.add_conditional_edges(
    NodeId.TRIAGE.value,
    traverse,
    path_map,
)

graph.add_edge(NodeId.CHECK_ORDER_STATUS.value, END)
graph.add_edge(NodeId.CHECK_PRICE.value, END)
graph.add_edge(NodeId.ANSWER_POLICY_QUESTION.value, END)
graph.add_edge(NodeId.GREET.value, END)
graph.add_conditional_edges(NodeId.HANDLE_COMPOSITE.value, traverse, path_map)

app = graph.compile()

messages = [
    "I want to know the prices of jackets, and I want to return a game I bought"
]

i = 0

for message in messages:
    result = app.invoke(ConversationState(
        id=f"test-{i}",
        message=message,
    ))

    print(result)
    i = i + 1
