from models.conversation_state import ConversationState
from models.order import Order
from models.order_status import ShippedStatus, DeliveredStatus, CancelledStatus, ProcessingStatus
from services.order_service import get_order_by_id
from services.policy_qa_service import answer_policy_question
from services.product_service import get_products_by_name
from services.triage_service import triage_message


def triage_node(state: ConversationState) -> ConversationState:
    result = triage_message(state.message)
    state.triage_result = result
    return state


def format_order_status(order: Order) -> str:
    match order.status:
        case ProcessingStatus():
            return f"Your order {order.id} is still being processed."
        case ShippedStatus():
            return f"Your order {order.id} shipped."
        case DeliveredStatus(delivered_at=delivered_at):
            return f"Your order {order.id} was delivered on {delivered_at}."
        case CancelledStatus():
            return f"Your order {order.id} was cancelled."


def check_order_status_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check order status on a conversation state with triage_result None")
    else:
        order_id = triage_result.order_id
        if order_id is not None:
            order = get_order_by_id(order_id)
            if order is None:
                state.outcomes["order_status"] = f"I couldn't find an order with ID {order_id}."
                return state
            else:
                state.order = order
                message = format_order_status(order)
                state.outcomes["order_status"] = message
                return state
        else:
            state.outcomes["order_status"] = "Could you share your order ID so I can look that up?"
            return state


def check_price_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        product_ref = triage_result.product_reference
        if product_ref is not None:
            products = get_products_by_name(product_ref)
            if not products:
                state.outcomes["price_check"] = "I couldn't find the product you're asking for."
                return state
            else:
                message = f"I found these products matching your query: {products}"
                state.outcomes["price_check"] = message
                return state
        else:
            state.outcomes["price_check"] = "I couldn't find the product you're asking for."
            return state


def answer_policy_question_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        result = answer_policy_question(question=state.message, top_k=2)
        state.outcomes["policy_question"] = result.answer
        return state
