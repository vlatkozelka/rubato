from mcp_server.instance import mcp
from models.triage_result import TriageResult
from services.triage_service import triage_message


@mcp.tool()
async def triage_message_tool(message: str) -> TriageResult:
    """
    Classify a customer support message into an intent, extracting any
    order ID, product reference, and sentiment expressed.
    """
    return await triage_message(message)
