from typing import List

from pydantic import BaseModel, Field


class ComplexCaseResolution(BaseModel):
    """Call this tool when you are finished investigating and ready to
        respond to the customer — including when you need to ask them a
        clarifying question (e.g. for a missing order ID) rather than a
        final decision. This is the ONLY way to send a reply back to the
        customer; do not attempt to communicate with them through any other
        tool."""
    customer_message: str = Field(
        description="The full reply to send back to the customer. Plain, "
                     "warm, no internal policy mechanics or reasoning."
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