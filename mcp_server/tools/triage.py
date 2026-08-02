from mcp_server.instance import mcp
from models.triage_result import TriageResult
from models.turn import Turn
from services.triage_service import triage_message


@mcp.tool()
async def triage_message_tool(message: str, history: list[Turn] | None = None) -> TriageResult:
    """
    Classify a customer support message into an intent, extracting any
    order ID, product reference, and sentiment expressed. `history`, if
    provided, is prior conversation turns used to resolve what the
    current message refers to (e.g. an order ID given in reply to a
    clarifying question).
    """
    return await triage_message(message, history)
