from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import AIMessage, HumanMessage
from langfuse import get_client as get_langfuse_client

from graph.graph_utils import extract_observations, build_tool_registry
from mcp_client.client import get_safe_langchain_tools
from models.conversation_state import ConversationState
from models.decisions import ComplexCaseResolution
from services.llm_factory import get_agent_client


async def call_agent(state: ConversationState) -> ConversationState:
    langfuse_client = get_langfuse_client()
    langfuse_prompt = langfuse_client.get_prompt("agent/react")
    system_prompt = langfuse_prompt.compile(customer_id=state.customer_id)
    messages = [
        HumanMessage(content=turn.content) if turn.role == "user"
        else AIMessage(content=turn.content)
        for turn in state.history
    ]
    messages.append(HumanMessage(content=state.message))

    tools = await get_safe_langchain_tools()
    tools_dict = build_tool_registry(tools)

    agent_client = get_agent_client(profile_name="qwen3_thinking")
    result = await agent_client(
        messages=messages,
        tools=tools,
        system_prompt=system_prompt,
        tool_strategy=ToolStrategy(ComplexCaseResolution),
        prompt=langfuse_prompt
    )
    observations = extract_observations(result["messages"], tools_dict)
    resolution: ComplexCaseResolution = result["structured_response"]

    state.reply = resolution.reply
    state.citations = resolution.citations or None
    state.observations = observations
    state.complex_case_resolution = resolution

    return state
