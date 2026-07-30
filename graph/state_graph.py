from langgraph.constants import END
from langgraph.graph import StateGraph

from graph.nodes import triage_node, check_order_status_node
from models.conversation_state import ConversationState

graph = StateGraph(ConversationState)
graph.add_node("triage", triage_node)
graph.add_node("check_order_status", check_order_status_node)
graph.set_entry_point("triage")


def traverse(state: ConversationState) -> str:
    if state.triage_result is None:
        raise ValueError("traverse called with triage_result = None")
    else:
        match state.triage_result.intent:

            case "order_status":
                return "check_order_status"
            case "policy_question":
                return "answer_policy_question"
            case "return_request":
                return "handle_return_request"
            case "refund_request":
                return "handle_refund_request"
            case "price_check":
                return "check_price"
            case "escalate":
                return "assign_to_human"
            case "chitchat":
                return "greet"
            case "composite":
                return "handle_composite"
            case "complex_case":
                return "process_complex_case"


graph.add_conditional_edges(
    "triage",
    traverse,
    {
        "check_order_status": "check_order_status",
        # everything else routes to END until those nodes exist
        "answer_policy_question": END,
        "handle_return_request": END,
        "handle_refund_request": END,
        "check_price": END,
        "assign_to_human": END,
        "greet": END,
        "handle_composite": END,
        "process_complex_case": END,
    },
)

graph.add_edge("check_order_status", END)

app = graph.compile()

result = app.invoke(ConversationState(
    id="test-1",
    message="Where's my order ord_1002?",
    outcomes={},
))

print(result)
