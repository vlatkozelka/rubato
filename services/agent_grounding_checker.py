import logging
import re

from models.decisions import ComplexCaseResolution

logger = logging.getLogger(__name__)

# Only the tools capable of a real state change need grounding — read-only
# lookups never need a "did this actually happen" check. This list is the
# money-moving/state-changing surface of the whole agent.
ACTION_CLAIM_PATTERNS: dict[str, list[str]] = {
    "create_approval_tool": [
        r"\bapprov\w*\b",
        r"refund.{0,20}(has been|is|was)\s+(processed|issued|approved)",
        r"i(?:'ve| have)\s+(approved|processed|issued)",
    ],
    "initiate_return_tool": [
        r"return.{0,20}(has been|is|was)\s+(initiated|started|processed)",
        r"i(?:'ve| have)\s+(initiated|started)\s+your\s+return",
    ],
}

FALLBACK_MESSAGE = (
    "Thanks for the details — I've recorded everything about your case, "
    "but no refund or return has been processed yet. A member of our "
    "team will review it and follow up with next steps."
)


def _successful_tools(observations: list[dict]) -> set[str]:
    successful = set()
    for obs in observations:
        tool = obs.get("tool")
        if not tool:
            continue
        result = obs.get("result")
        if isinstance(result, dict) and "error" in result:
            continue
        successful.add(tool)
    return successful


def _claimed_tools(text: str) -> set[str]:
    claimed = set()
    for tool_name, patterns in ACTION_CLAIM_PATTERNS.items():
        if any(re.search(p, text, re.IGNORECASE) for p in patterns):
            claimed.add(tool_name)
    return claimed


def enforce_grounding(
    resolution: ComplexCaseResolution, observations: list[dict]
) -> ComplexCaseResolution:
    """Strip/replace claims of an executed action that have no backing
    successful tool call in this run's observations.

    Not a general fact-checker — narrowly targets the already-reproduced
    failure mode of the resolver narrating a refund/return that never
    actually ran.
    """
    successful = _successful_tools(observations)
    claimed = _claimed_tools(resolution.customer_message)
    ungrounded = claimed - successful

    if not ungrounded:
        return resolution

    logger.warning(
        "ungrounded_action_claim",
        extra={
            "event": "ungrounded_action_claim",
            "claimed_tools": list(ungrounded),
            "successful_tools": list(successful),
            "original_customer_message": resolution.customer_message,
            "reasoning": resolution.reasoning,
        },
    )

    return resolution.model_copy(update={"customer_message": FALLBACK_MESSAGE})