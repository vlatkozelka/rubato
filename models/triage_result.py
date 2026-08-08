from typing import Literal, Optional
from pydantic import BaseModel

from models.intent import Intent


class TriageResult(BaseModel):
    intent: Intent
    order_id: Optional[str] = None
    product_reference: Optional[str] = None
    sentiment: Literal["neutral", "frustrated", "angry"] = "neutral"
    reasoning: str
