from logging import Logger

from app.timing import log_duration
from graph.nodes.simple_nodes import _get_order
from mcp_client.client import call_tool
from models.approval import Approval, ApprovalStatus
from models.conversation_state import ConversationState
from services import refund_service
from services.customer_service import increment_refund_request_count

logger = Logger("check_refund_node")


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
            approval = await refund_service.check_refund(
                order_id=order_id,
                product_id=product_id,
                customer_id=state.customer_id,
                reason=state.message
            )

    if approval is None:
        logger.warning("refund_request_rejected", extra={"event": "refund_request_rejected", "order_id": order_id})
        state.reply = "I couldn't process a refund for that order."
        return state

    create_result = await call_tool("create_approval_tool", {
        "payload": approval.payload.model_dump(mode="json"),
    })

    approval = Approval.model_validate(create_result.structuredContent)
    await increment_refund_request_count(state.customer_id)

    if approval.payload.status == ApprovalStatus.DENIED:
        state.reply = f"I'm sorry, I can't approve this refund: {approval.payload.reason}"
    else:
        state.reply = "Your refund request has been submitted and is pending review by our team."
    return state
