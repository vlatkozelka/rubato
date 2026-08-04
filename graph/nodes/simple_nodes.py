import logging
from typing import List, Optional

from app.timing import log_duration
from mcp_client.client import call_tool
from models.approval import Approval, ApprovalStatus
from models.conversation_state import ConversationState
from models.order import Order
from models.order_item import OrderItem
from models.order_status import ShippedStatus, DeliveredStatus, CancelledStatus, ProcessingStatus
from models.policy_answer import PolicyAnswer
from models.product import Product
from models.triage_result import TriageResult
from services.customer_service import increment_refund_request_count

logger = logging.getLogger("rubato.nodes")


async def _get_order(order_id: str) -> Optional[Order]:
    result = await call_tool("get_order_by_id_tool", {"order_id": order_id})
    order_data = result.structuredContent["result"]
    return Order.model_validate(order_data) if order_data else None


async def triage_node(state: ConversationState) -> ConversationState:
    result = await call_tool("triage_message_tool", {
        "message": state.message,
        "history": [t.model_dump(mode="json") for t in state.history],
    })
    state.triage_result = TriageResult.model_validate(result.structuredContent)
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


async def check_order_status_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check order status on a conversation state with triage_result None")
    else:
        order_id = triage_result.order_id
        if order_id is not None:
            with log_duration(logger, "order_lookup_finished", order_id=order_id):
                order = await _get_order(order_id)
            if order is None:
                logger.warning("order_not_found", extra={"event": "order_not_found", "order_id": order_id})
                state.reply = f"I couldn't find an order with ID {order_id}."
                return state
            else:
                state.order = order
                state.reply = format_order_status(order)
                return state
        else:
            logger.info("order_id_missing", extra={"event": "order_id_missing"})
            state.reply = "Could you share your order ID so I can look that up?"
            return state


def format_price_matches(products: List[Product]) -> str:
    lines = [
        f"- {p.name}{f' ({p.size})' if p.size else ''}: ${p.price:.2f}"
        + ("" if p.stock > 0 else " — out of stock")
        for p in products
    ]
    return "Here's what I found:\n" + "\n".join(lines)


async def check_price_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")

    product_ref = triage_result.product_reference
    if product_ref is None:
        logger.info("product_reference_missing", extra={"event": "product_reference_missing"})
        state.reply = "I couldn't find the product you're asking for."
        return state

    with log_duration(logger, "product_lookup_finished", query=product_ref):
        result = await call_tool("get_products_by_name_tool", {"name": product_ref, "limit": 20})

    products = [Product.model_validate(p) for p in result.structuredContent["result"]]

    if not products:
        logger.warning("product_not_found", extra={"event": "product_not_found", "query": product_ref})
        state.reply = "I couldn't find the product you're asking for."
        return state

    state.reply = format_price_matches(products)
    return state


async def answer_policy_question_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        result = await call_tool("answer_policy_question_tool", {"question": state.message, "top_k": 2})
        policy_answer = PolicyAnswer.model_validate(result.structuredContent)
        state.reply = policy_answer.answer
        state.citations = policy_answer.cited_sources or None
        return state


async def refund_request_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing refund_request_node on a conversation state with triage_result None")

    order_id = triage_result.order_id
    if order_id is None:
        state.reply = "Sure, which order would you like refunded?"
        return state

    order = await _get_order(order_id)

    approval = None
    if order is not None and order.items and state.customer_id is not None:
        product_id = order.items[0].product_id
        with log_duration(logger, "refund_check_finished", order_id=order_id):
            check_result = await call_tool("check_refund_tool", {
                "order_id": order_id,
                "product_id": product_id,
                "customer_id": state.customer_id,
                "reason": state.message,
            })
        approval_data = check_result.structuredContent["result"]
        approval = Approval.model_validate(approval_data) if approval_data else None

    if approval is None:
        logger.warning("refund_request_rejected", extra={"event": "refund_request_rejected", "order_id": order_id})
        state.reply = "I couldn't process a refund for that order."
        return state

    create_result = await call_tool("create_approval_tool", {"approval": approval.model_dump(mode="json")})

    approval = Approval.model_validate(create_result.structuredContent)
    await increment_refund_request_count(state.customer_id)

    if approval.status == ApprovalStatus.DENIED:
        state.reply = f"I'm sorry, I can't approve this refund: {approval.payload.reason}"
    else:
        state.reply = "Your refund request has been submitted and is pending review by our team."
    return state


async def return_request_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing return_request_node on a conversation state with triage_result None")

    order_id = triage_result.order_id
    order = await _get_order(order_id) if order_id else None

    item = None
    if order is not None and order.items and state.customer_id is not None:
        product_id = order.items[0].product_id
        with log_duration(logger, "return_initiation_finished", order_id=order_id):
            initiate_result = await call_tool("initiate_return_tool", {
                "order_id": order_id,
                "product_id": product_id,
                "customer_id": state.customer_id,
                "reason": state.message,
            })
        item_data = initiate_result.structuredContent["result"]
        item = OrderItem.model_validate(item_data) if item_data else None

    if item is None:
        logger.warning("return_request_rejected", extra={"event": "return_request_rejected", "order_id": order_id})
        state.reply = "I couldn't start a return for that order."
        return state

    state.reply = f"Your return for {item.name} has been started."
    return state


async def greet_node(state: ConversationState) -> ConversationState:
    greeting_message = f"""
Hi! I'm here to help with your orders and questions about our store. I can:

- Check the status of an order
- Answer questions about our policies (returns, shipping, warranty)
- Look up prices on our products
- Help you start a return

Just let me know what you need!"""
    state.reply = greeting_message
    return state
