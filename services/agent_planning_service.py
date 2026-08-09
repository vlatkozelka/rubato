from typing import List

from langchain_core.tools import BaseTool
from langfuse import get_client as get_langfuse_client

from models.agent_observation import AgentObservation
from models.conversation_state import ConversationState
from models.decisions import ComplexCaseResolution
from models.llm_profile import default_non_thinking_model
from models.plan import Plan
from services.llm_factory import get_async_instructor_client


async def create_agent_plan(conversation_state: ConversationState, tools: List[BaseTool]) -> Plan:
    client = get_async_instructor_client(default_non_thinking_model)
    langfuse_client = get_langfuse_client()

    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description}" for t in tools
    )

    langfuse_prompt = langfuse_client.get_prompt("agent/plan/create_plan")
    prompt = langfuse_prompt.compile(
        customer_message=conversation_state.message,
        customer_id=conversation_state.customer_id,
        tool_descriptions=tool_descriptions,
    )

    return await client(
        prompt=langfuse_prompt,
        response_model=Plan,
        messages=[{"role": "user", "content": prompt}],
    )


async def resolve_from_observations(state: ConversationState,
                                    observations: list[AgentObservation]) -> ComplexCaseResolution:
    client = get_async_instructor_client(default_non_thinking_model)
    langfuse_client = get_langfuse_client()

    obs_text = "\n".join(
        f"Step {o.step_id} ({o.tool}): {o.result}"
        for o in observations
    ) or "No steps produced observations."

    langfuse_prompt = langfuse_client.get_prompt("agent/plan/resolve_observations")
    prompt = langfuse_prompt.compile(
        customer_message=state.message,
        observations=obs_text,
    )

    return await client(
        prompt=langfuse_prompt,
        response_model=ComplexCaseResolution,
        messages=[{"role": "user", "content": prompt}],
    )
