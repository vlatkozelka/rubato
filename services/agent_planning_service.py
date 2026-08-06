from typing import List

from langchain_core.tools import BaseTool

from models.agent_observation import AgentObservation
from models.conversation_state import ConversationState
from models.decisions import ComplexCaseResolution
from models.plan import Plan
from services.llm_factory import get_async_instructor_client


async def create_agent_plan(conversation_state: ConversationState, tools: List[BaseTool]) -> Plan:
    client = get_async_instructor_client("qwen3_non_thinking")

    tool_descriptions = "\n".join(
        f"- {t.name}: {t.description}" for t in tools
    )

    prompt = f"""
You are a customer support agent at an e-commerce store
Your task is to generate a plan to resolve a customer's case given the following data

Customer Message: {conversation_state.message}
Customer ID: {conversation_state.customer_id}

You can use these tools to build your plan:

{tool_descriptions}

Produce an ordered list of steps to investigate and resolve this case.
Each step should reference a tool_hint if one clearly applies, or null if
the step is reasoning-only (e.g. the final decision step).
Limit steps to 20 maximum. Aim for minimizing the number of steps
"""

    return await client(
        response_model=Plan,
        messages=[{"role": "user", "content": prompt}],
    )


async def resolve_from_observations(state: ConversationState, observations: list[AgentObservation]) -> ComplexCaseResolution:
    client = get_async_instructor_client("qwen3_non_thinking")

    obs_text = "\n".join(
        f"Step {o.step_id} ({o.tool}): {o.result}"
        for o in observations
    ) or "No steps produced observations."

    prompt = f"""
Original customer inquiry: {state.message}

You investigated this case and gathered the following observations:
{obs_text}

Based on these observations, decide how to resolve the case. If a
necessary observation is missing or failed, resolve as best you can
given what's available, or indicate more information is needed from
the customer.
"""

    return await client(
        response_model=ComplexCaseResolution,
        messages=[{"role": "user", "content": prompt}],
    )
