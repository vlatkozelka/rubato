from mcp_server.instance import mcp
from models.retrieved_chunk import RetrievedChunk
from services.retrieval_service import retrieve_policy_excerpts


@mcp.tool()
async def retrieve_policy_excerpts_tool(question: str, top_k: int = 5) -> list[RetrievedChunk]:
    """
    Retrieve ranked policy document excerpts relevant to a customer question
    (returns, shipping, warranty), via hybrid search and reranking. Returns a
    list of chunks, each with its source document, rank, and relevance
    scores — does not synthesize an answer.
    """
    return await retrieve_policy_excerpts(question, top_k)