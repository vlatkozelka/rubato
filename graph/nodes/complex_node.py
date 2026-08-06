from langchain_core.runnables import RunnableConfig

from app.config import DEFAULT_AGENT_MODE
from graph.plan_executor import execute_plan
from graph.re_act_agent import call_agent
from mcp_client.client import get_safe_langchain_tools
from models.agent_mode import AgentMode
from models.agent_observation import parse_observations
from models.conversation_state import ConversationState
from services.agent_planning_service import create_agent_plan, resolve_from_observations


async def complex_case_node(state: ConversationState, config: RunnableConfig) -> ConversationState:
    mode = config.get("configurable", {}).get("agent_mode", DEFAULT_AGENT_MODE)
    print(f"agent mode: {mode}")

    if mode == AgentMode.PLAN:
        return await _resolve_plan_execute(state)
    return await call_agent(state)


async def _resolve_plan_execute(state: ConversationState) -> ConversationState:
    tools = await get_safe_langchain_tools()

    plan = await create_agent_plan(state, tools)
    observations_string = await execute_plan(plan, tools, state.customer_id, state.message)
    observations = parse_observations(observations_string)

    resolution = await resolve_from_observations(state, observations)
    state.reply = resolution.reply
    state.citations = resolution.citations or None
    state.observations = observations
    state.complex_case_resolution = resolution
    return state
