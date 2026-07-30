from typing import Optional, Dict

from pydantic import BaseModel, Field

from models.customer import Customer
from models.intent import Intent
from models.order import Order
from models.triage_result import TriageResult


class ConversationState(BaseModel):
    id: str
    message: str
    customer: Optional[Customer] = None
    order: Optional[Order] = None
    triage_result: Optional[TriageResult] = None
    outcomes: Dict[Intent, str] = Field(default_factory=dict)
    escalated_to: Optional[str] = None
