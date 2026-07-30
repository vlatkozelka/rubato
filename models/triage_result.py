from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from models.intent import Intent

SimpleIntent = Literal[
    Intent.ORDER_STATUS,
    Intent.POLICY_QUESTION,
    Intent.RETURN_REQUEST,
    Intent.REFUND_REQUEST,
    Intent.PRICE_CHECK
]


class TriageResult(BaseModel):
    intent: Intent
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
