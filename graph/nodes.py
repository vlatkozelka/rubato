import logging
from typing import List

from app.timing import log_duration
from models.approval import ApprovalStatus
from models.conversation_state import ConversationState
from models.intent import Intent
from models.intent_result import IntentResult
from models.order import Order
from models.order_status import ShippedStatus, DeliveredStatus, CancelledStatus, ProcessingStatus
from models.product import Product
from services.approval_service import create_approval
from services.order_service import get_order_by_id
from services.policy_service import answer_policy_question
from services.product_service import get_products_by_name
from services.refund_service import check_refund
from services.return_service import initiate_return
from services.triage_service import triage_message

logger = logging.getLogger("rubato.nodes")


async def triage_node(state: ConversationState) -> ConversationState:
    result = await triage_message(state.message)
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


async def check_order_status_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check order status on a conversation state with triage_result None")
    else:
        order_id = triage_result.order_id
        if order_id is not None:
            with log_duration(logger, "order_lookup_finished", order_id=order_id):
                order = await get_order_by_id(order_id)
            if order is None:
                logger.warning("order_not_found", extra={"event": "order_not_found", "order_id": order_id})
                state.results.append(
                    IntentResult(intent=Intent.ORDER_STATUS, result=f"I couldn't find an order with ID {order_id}."))
                return state
            else:
                state.order = order
                message = format_order_status(order)
                state.results.append(IntentResult(intent=Intent.ORDER_STATUS, result=message))
                return state
        else:
            logger.info("order_id_missing", extra={"event": "order_id_missing"})
            state.results.append(
                IntentResult(intent=Intent.ORDER_STATUS, result="Could you share your order ID so I can look that up?"))
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
    else:
        product_ref = triage_result.product_reference
        if product_ref is not None:
            with log_duration(logger, "product_lookup_finished", query=product_ref):
                products = await get_products_by_name(product_ref)
            if not products:
                logger.warning("product_not_found", extra={"event": "product_not_found", "query": product_ref})
                state.results.append(
                    IntentResult(intent=Intent.PRICE_CHECK, result="I couldn't find the product you're asking for."))
                return state
            else:
                message = format_price_matches(products)
                state.results.append(IntentResult(intent=Intent.PRICE_CHECK, result=message))
                return state
        else:
            logger.info("product_reference_missing", extra={"event": "product_reference_missing"})
            state.results.append(
                IntentResult(intent=Intent.PRICE_CHECK, result="I couldn't find the product you're asking for."))
            return state


async def answer_policy_question_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        result = await answer_policy_question(question=state.message, top_k=2)
        state.results.append(IntentResult(
            intent=Intent.POLICY_QUESTION,
            result=result.answer,
            citations=result.cited_sources or None,
        ))
        return state


async def refund_request_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing refund_request_node on a conversation state with triage_result None")

    order_id = triage_result.order_id
    order = await get_order_by_id(order_id) if order_id else None

    approval = None
    if order is not None and order.items and state.customer_id is not None:
        product_id = order.items[0].product_id
        with log_duration(logger, "refund_check_finished", order_id=order_id):
            approval = await check_refund(order_id, product_id, state.customer_id, state.message)

    if approval is None:
        logger.warning("refund_request_rejected", extra={"event": "refund_request_rejected", "order_id": order_id})
        state.results.append(
            IntentResult(intent=Intent.REFUND_REQUEST, result="I couldn't process a refund for that order."))
        return state

    approval = await create_approval(approval)
    if approval.status == ApprovalStatus.DENIED:
        message = f"I'm sorry, I can't approve this refund: {approval.payload.reason}"
    else:
        message = "Your refund request has been submitted and is pending review by our team."
    state.results.append(IntentResult(intent=Intent.REFUND_REQUEST, result=message))
    return state


async def return_request_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing return_request_node on a conversation state with triage_result None")

    order_id = triage_result.order_id
    order = await get_order_by_id(order_id) if order_id else None

    item = None
    if order is not None and order.items and state.customer_id is not None:
        product_id = order.items[0].product_id
        with log_duration(logger, "return_initiation_finished", order_id=order_id):
            item = await initiate_return(order_id, product_id, state.customer_id, state.message)

    if item is None:
        logger.warning("return_request_rejected", extra={"event": "return_request_rejected", "order_id": order_id})
        state.results.append(
            IntentResult(intent=Intent.RETURN_REQUEST, result="I couldn't start a return for that order."))
        return state

    state.results.append(
        IntentResult(intent=Intent.RETURN_REQUEST, result=f"Your return for {item.name} has been started."))
    return state


async def greet_node(state: ConversationState) -> ConversationState:
    greeting_message = f"""
Hi! I'm here to help with your orders and questions about our store. I can:

- Check the status of an order
- Answer questions about our policies (returns, shipping, warranty)
- Look up prices on our products
- Help you start a return

Just let me know what you need!"""
    state.results.append(IntentResult(intent=Intent.CHITCHAT, result=greeting_message))
    return state


async def composite_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing composite_node on a conversation state with triage_result None")
    else:
        sub_intents = triage_result.sub_intents
        if not sub_intents:
            raise ValueError("performing composite_node on a conversation state with no sub intents")
        else:
            # todo add memory to handle other intents
            first_sub_intent = sub_intents[0]
            state.results.append(IntentResult(intent=Intent.COMPOSITE,
                                              result=f"I will help you resolve {first_sub_intent.value.replace('_', ' ')} first and then we'll handle the rest"))
            state.triage_result.intent = first_sub_intent
        return state
