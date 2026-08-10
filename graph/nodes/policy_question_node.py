from mcp_client.client import call_tool
from models.conversation_state import ConversationState
from models.policy_answer import PolicyAnswer
from services.policy_service import answer_policy_question


async def answer_policy_question_node(state: ConversationState) -> ConversationState:
    triage_result = state.triage_result
    question = state.message
    if triage_result is None:
        raise ValueError("performing check_price on a conversation state with triage_result None")
    else:
        excerpts = await call_tool("retrieve_policy_excerpts_tool", {"question": question, "top_k": 5})
        policy_answer = PolicyAnswer.model_validate(await answer_policy_question(question=question, excerpts=excerpts))
        state.reply = policy_answer.answer
        state.citations = policy_answer.cited_sources or None
        return state
