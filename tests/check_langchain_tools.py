import asyncio
import json
import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8001/mcp")
MCP_SERVER_NAME = "rubato-tools"


async def main():
    client = MultiServerMCPClient(
        {
            MCP_SERVER_NAME: {
                "transport": "http",
                "url": MCP_SERVER_URL,
                "headers": {"Authorization": f"Bearer {os.environ['MCP_SHARED_KEY']}"},
            }
        }
    )

    import inspect
    from mcp import ClientSession
    print(inspect.signature(ClientSession.call_tool))

    tools = await client.get_tools()
    print("=== Tool names ===")
    print(", ".join(t.name for t in tools))
    target_tool = next(t for t in tools if t.name == "get_return_history_tool")

    result = await target_tool.ainvoke({"customer_id": "cust_006"})

    print("=== RAW MCP RESULT ===")
    print(repr(result))

    # unwrap the text-block shape and try to parse it as JSON
    raw_text = result[0]["text"]
    print("\n=== RAW TEXT FIELD ===")
    print(repr(raw_text))

    try:
        parsed = json.loads(raw_text)
        print("\n=== PARSED AS JSON ===")
        print(parsed)
        print(type(parsed))
    except json.JSONDecodeError:
        print("\n(not valid JSON — it's just a plain string/number)")


asyncio.run(main())
