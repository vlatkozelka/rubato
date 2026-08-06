from typing import List

import instructor
from langchain_core.tools import BaseTool
from openai import AsyncOpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from models.conversation_state import ConversationState
from models.decisions import ComplexCaseResolution
from models.plan import Plan


async def create_agent_plan(conversation_state: ConversationState, tools: List[BaseTool]) -> Plan:
    client = instructor.from_openai(
        AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
        mode=instructor.Mode.JSON_SCHEMA,
    )

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

    return await client.chat.completions.create(
        model=LLM_MODEL,
        response_model=Plan,
        messages=[{"role": "user", "content": prompt}],
        extra_body={
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 1.5,
            "repetition_penalty": 1.0,
        }
    )


async def resolve_from_observations(state: ConversationState, observations: list[dict]) -> ComplexCaseResolution:
    client = instructor.from_openai(
        AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
        mode=instructor.Mode.JSON_SCHEMA,
    )

    obs_text = "\n".join(
        f"Step {o['step_id']} ({o['tool']}): {o['result']}"
        for o in observations
    ) or "No steps produced observations."

    prompt = f"""
Customer message: {state.message}

You investigated this case and gathered the following observations:
{obs_text}

Based on these observations, decide how to resolve the case. If a
necessary observation is missing or failed, resolve as best you can
given what's available, or indicate more information is needed from
the customer.
"""

    return await client.chat.completions.create(
        model=LLM_MODEL,
        response_model=ComplexCaseResolution,
        messages=[{"role": "user", "content": prompt}],
        extra_body={
            "chat_template_kwargs": {"enable_thinking": False},
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 1.5,
            "repetition_penalty": 1.0,
        }
    )
