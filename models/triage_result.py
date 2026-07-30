from typing import List, Literal, Optional
from pydantic import BaseModel, Field

SimpleIntent = Literal[
    "order_status",
    "policy_question",
    "return_request",
    "refund_request",
    "price_check"
]


class TriageResult(BaseModel):
    intent: Literal[
        "order_status",
        "policy_question",
        "return_request",
        "refund_request",
        "price_check",
        "escalate",
        "chitchat",
        "composite",
        "complex_case",
    ]
    sub_intents: Optional[List[SimpleIntent]] = Field(
        default=None,
        description=(
            "Every simple intent detected in the message, whenever more "
            "than one is present — whether they are independent "
            "(intent='composite') or conflicting (intent='complex_case'). "
            "Leave empty/None when only one intent is present."
        ),
    )
    order_id: Optional[str] = None
    product_reference: Optional[str] = None
    sentiment: Literal["neutral", "frustrated", "angry"] = "neutral"