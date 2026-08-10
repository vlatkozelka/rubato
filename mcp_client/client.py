import os

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langfuse._client.get_client import get_client as get_langfuse_client
from langfuse._client.observe import observe
from opentelemetry import context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

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

_propagator = TraceContextTextMapPropagator()


def _inject_trace_context() -> dict:
    carrier = {}
    _propagator.inject(carrier, context=context.get_current())
    return carrier


@observe(as_type="tool", capture_output=False)
async def call_tool(tool_name: str, arguments: dict):
    """
    Call a named tool directly, bypassing LangChain's agent-oriented Tool
    wrapping — appropriate here because the graph, not an LLM, decides
    which tool to call. Opens a fresh session per call (stateless), matching
    the library's default and this server's lack of cross-call state.

    Trace span is named after the actual tool called, not "call_tool", and
    logs parsed structuredContent (or raw content as fallback) instead of
    the full CallToolResult envelope — the envelope is transport plumbing,
    not something worth reading in a trace.
    """
    get_langfuse_client().update_current_span(name=tool_name, input=arguments)

    async with client.session(MCP_SERVER_NAME) as session:
        result = await session.call_tool(
            tool_name,
            arguments,
            meta=_inject_trace_context(),
        )

    output = result.structuredContent["result"] if result.structuredContent else result.content
    get_langfuse_client().update_current_span(output=output)

    return result


async def get_langchain_tools():
    return await client.get_tools()


async def get_safe_langchain_tools():
    """
    Wraps get_langchain_tools() output so empty tool results produce a
    legible string ("[]") instead of an empty list, which otherwise
    collapses to nothing when serialized into the model's prompt —
    confirmed via debug trace: a blank result after 'Tool:' with no
    content at all.
    """
    raw_tools = await get_langchain_tools()
    safe_tools = []

    for t in raw_tools:
        @observe(as_type="tool", name=t.name)
        async def _coro(_tool=t, **kwargs):
            content, artifact = await _tool.coroutine(**kwargs)
            if not content:
                content = "[]"
            return content, artifact

        safe_tools.append(
            StructuredTool(
                name=t.name,
                description=t.description,
                args_schema=t.args_schema,
                coroutine=_coro,
                response_format="content_and_artifact",
            )
        )

    return safe_tools
