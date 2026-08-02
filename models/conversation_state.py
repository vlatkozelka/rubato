from typing import Optional, List

from pydantic import BaseModel, Field

from models.customer import Customer
from models.intent_result import IntentResult
from models.order import Order
from models.triage_result import TriageResult
from models.turn import Turn


class ConversationState(BaseModel):
    id: str
    message: str
    customer_id: Optional[str] = None
    customer: Optional[Customer] = None
    order: Optional[Order] = None
    triage_result: Optional[TriageResult] = None
    results: List[IntentResult] = Field(default_factory=list)
    escalated_to: Optional[str] = None
    history: List[Turn] = Field(default_factory=list)
