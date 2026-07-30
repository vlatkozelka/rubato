from models.conversation_state import ConversationState
from models.order_status import ShippedStatus, DeliveredStatus, CancelledStatus, ProcessingStatus
from services.triage_service import triage_message
from services.order_service import get_order_by_id
from models.order import Order


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
