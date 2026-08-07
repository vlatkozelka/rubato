from mcp_server.instance import mcp
from services.retrieval_service import retrieve_policy_excerpts


@mcp.tool()
async def retrieve_policy_excerpts_tool(question: str, top_k: int = 3) -> str:
    """
    Retrieve ranked policy document excerpts relevant to a customer question
    (returns, shipping, warranty), via hybrid search and reranking. Returns
    raw excerpts with their source — does not synthesize an answer.
    """
    return await retrieve_policy_excerpts(question, top_k)
