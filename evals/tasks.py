from uuid import uuid4

from graph.nodes.simple_nodes import triage_node
from models.conversation_state import ConversationState


async def triage_task(*, item, **kwargs):
    state = ConversationState(
        id=str(uuid4()),
        message=item.input["message"],
        customer_id=item.input["customer_id"],
    )
    result = await triage_node(state)
    if result.triage_result is None:
        return None
    else:
        return {"intent": result.triage_result.intent.value}
