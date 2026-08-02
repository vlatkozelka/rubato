import asyncio
import os

from langchain_mcp_adapters.client import MultiServerMCPClient

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8001/mcp")
MCP_SERVER_NAME = "rubato-tools"

client = MultiServerMCPClient(
    {
        MCP_SERVER_NAME: {
            "transport": "http",
            "url": MCP_SERVER_URL,
            "headers": {"Authorization": f"Bearer {os.environ['MCP_SHARED_KEY']}"},
        }
    }
)


async def call_tool(tool_name: str, arguments: dict):
    """
    Call a named tool directly, bypassing LangChain's agent-oriented Tool
    wrapping — appropriate here because the graph, not an LLM, decides
    which tool to call. Opens a fresh session per call (stateless), matching
    the library's default and this server's lack of cross-call state.
    """
    async with client.session(MCP_SERVER_NAME) as session:
        return await session.call_tool(tool_name, arguments)
