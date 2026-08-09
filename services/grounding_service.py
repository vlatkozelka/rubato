import logging

from langfuse import get_client as get_langfuse_client

from models.agent_observation import AgentObservation
from models.decisions import ComplexCaseResolution
from models.grounding_verdict import GroundingVerdict
from models.llm_profile import default_non_thinking_model
from services.llm_factory import get_async_instructor_client

logger = logging.getLogger(__name__)

client = get_async_instructor_client(default_non_thinking_model)


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
    langfuse_client = get_langfuse_client()
    langfuse_prompt = langfuse_client.get_prompt("agent/grounding/check_and_correct")
    prompt = langfuse_prompt.compile(
        customer_message=resolution.reply,
        tool_reference=_format_tool_reference(observations=observations, tool_registry=tools_registry),
        observations=_format_observations(observations=observations),
    )

    verdict = await client(
        prompt=langfuse_prompt,
        response_model=GroundingVerdict,
        messages=[{"role": "user", "content": prompt}],
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
