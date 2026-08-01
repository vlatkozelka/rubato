import logging
from typing import List

from app.timing import log_duration
from models.conversation_state import ConversationState
from models.intent import Intent
from models.intent_result import IntentResult
from models.order import Order
from models.order_status import ShippedStatus, DeliveredStatus, CancelledStatus, ProcessingStatus
from models.product import Product
from services.order_service import get_order_by_id
from services.policy_qa_service import answer_policy_question
from services.product_service import get_products_by_name
from services.triage_service import triage_message

logger = logging.getLogger("rubato.nodes")


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
            with log_duration(logger, "order_lookup_finished", order_id=order_id):
                order = get_order_by_id(order_id)
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
        f"- {p.name} ({p.size}): ${p.price:.2f}" + ("" if p.stock > 0 else " — out of stock")
        for p in products
    ]
    return "Here's what I found:\n" + "\n".join(lines)


def check_price_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        product_ref = triage_result.product_reference
        if product_ref is not None:
            with log_duration(logger, "product_lookup_finished", query=product_ref):
                products = get_products_by_name(product_ref)
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


def answer_policy_question_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        result = answer_policy_question(question=state.message, top_k=2)
        state.results.append(IntentResult(
            intent=Intent.POLICY_QUESTION,
            result=result.answer,
            citations=result.cited_sources or None,
        ))
        return state


def greet_node(state: ConversationState) -> ConversationState:
    greeting_message = f"""
Hi! I'm here to help with your orders and questions about our store. I can:

- Check the status of an order
- Answer questions about our policies (returns, shipping, warranty)
- Look up prices on our products
- Help you start a return

Just let me know what you need!"""
    state.results.append(IntentResult(intent=Intent.CHITCHAT, result=greeting_message))
    return state


def composite_node(state: ConversationState) -> ConversationState:
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
