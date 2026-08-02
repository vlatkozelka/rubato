from mcp_server.instance import mcp
from models.policy_answer import PolicyAnswer
from services.policy_service import answer_policy_question


@mcp.tool()
async def answer_policy_question_tool(question: str, top_k: int = 3) -> PolicyAnswer:
    """
    Answer a customer policy question (returns, shipping, warranty) using
    retrieved policy document excerpts, grounded to those excerpts only.
    """
    return await answer_policy_question(question, top_k)
