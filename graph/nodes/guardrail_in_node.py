import logging

from models.conversation_state import ConversationState
from services.injection_detector import InjectionDetector

logger = logging.getLogger(__name__)

GENERIC_REJECTION_MESSAGE = (
    "I'm not able to process that request. If you need help with an order, "
    "return, or policy question, please rephrase and I'll be glad to assist."
)


async def guardrail_in_node(
        state: ConversationState
) -> ConversationState:

    result = await InjectionDetector().check(state.message)

    if not result.flagged:
        return state

    logger.info(
        "injection_flagged customer_id=%s source=%s reason=%s message=%r",
        state.customer_id,
        result.source.value,
        result.reason,
        state.message,
    )

    state.reply = GENERIC_REJECTION_MESSAGE

    return state
