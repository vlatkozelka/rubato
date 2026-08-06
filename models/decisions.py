from typing import List

from pydantic import BaseModel, Field


class ComplexCaseResolution(BaseModel):
    """Call this tool when you are finished investigating and ready to
        respond to the customer — including when you need to ask them a
        clarifying question (e.g. for a missing order ID) rather than a
        final decision. This is the ONLY way to send a reply back to the
        customer; do not attempt to communicate with them through any other
        tool."""
    reply: str = Field(
        description="Your reply to the customer — written by you, addressing "
                    "their situation. This is NOT the customer's original "
                    "message repeated back; it is your response to it. "
                    "Plain, warm, no internal policy mechanics or reasoning."
    )
    reasoning: str = Field(
        description="Internal justification for this resolution, written "
                     "for a human reviewer — which facts you found (order "
                     "status, policy, return history, stock) and how they "
                     "led here. Not shown to the customer."
    )
    citations: List[str] = Field(
        default_factory=list,
        description="Policy doc sources used, if any policy question was answered.",
    )