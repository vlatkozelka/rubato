from models.conversation_state import ConversationState
from services.grounding_service import check_and_correct


async def agent_grounding_node(state: ConversationState) -> ConversationState:
    resolution = state.complex_case_resolution
    tools_registry = state.tools_registry
    if resolution is None or tools_registry is None:
        return state
    else:
        corrected_resolution = await check_and_correct(resolution=resolution,
                                                       observations=state.observations,
                                                       tools_registry=tools_registry)
        state.reply = corrected_resolution.reply
        state.citations = corrected_resolution.citations or None
        state.complex_case_resolution = corrected_resolution
        return state
