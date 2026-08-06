import logging

import instructor
from openai import AsyncOpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from models.agent_observation import AgentObservation
from models.decisions import ComplexCaseResolution
from models.grounding_verdict import GroundingVerdict

logger = logging.getLogger(__name__)

client = instructor.from_openai(
    AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
    mode=instructor.Mode.JSON_SCHEMA,
)


def _format_observations(observations: list[AgentObservation]) -> str:
    if not observations:
        return "No steps produced observations."
    return "\n".join(
        f"Step {o.step_id} ({o.tool}){f' — {o.description}' if o.description else ''}: {o.result}"
        for o in observations
    )


def _format_tool_reference(observations: list[AgentObservation], tool_registry: dict[str, str]) -> str:
    used_tools = {o.tool for o in observations}
    return "\n".join(
        f"- {name}: {tool_registry.get(name, 'no description available')}"
        for name in sorted(used_tools)
    )


async def check_and_correct(resolution: ComplexCaseResolution,
                            observations: list[AgentObservation],
                            tools_registry: dict[str, str]
                            ) -> ComplexCaseResolution:
    prompt = f"""
Customer-facing message: {resolution.reply}

Tool reference (what each tool actually does):
{_format_tool_reference(observations=observations, tool_registry=tools_registry)}

Observations from this run (the only things that actually happened):
{_format_observations(observations=observations)}

Does the customer-facing message claim any action was completed
(refund approved, return initiated, exchange processed, etc.) that is
NOT backed by a matching successful tool call above? Use the tool
reference to judge what each tool call actually accomplished — a tool
that creates a pending record is not the same as one that executes an
action. Only flag actual completed-action claims, not descriptions of
investigation or next steps.
"""

    verdict = await client.chat.completions.create(
        model=LLM_MODEL,
        response_model=GroundingVerdict,
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

    if not verdict.is_grounded:
        logger.warning(
            "ungrounded_action_claim",
            extra={
                "event": "ungrounded_action_claim",
                "ungrounded_claim": verdict.ungrounded_claim,
                "original_customer_message": resolution.reply,
            },
        )
        return resolution.model_copy(update={"customer_message": verdict.corrected_message})

    return resolution
