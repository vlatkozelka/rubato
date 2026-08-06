from typing import Optional, List

from pydantic import BaseModel, Field

from models.agent_observation import AgentObservation
from models.customer import Customer
from models.customer_profile import CustomerProfile
from models.decisions import ComplexCaseResolution
from models.order import Order
from models.triage_result import TriageResult
from models.turn import Turn


class ConversationState(BaseModel):
    id: str
    message: str
    customer_id: str
    customer: Optional[Customer] = None
    order: Optional[Order] = None
    triage_result: Optional[TriageResult] = None
    reply: Optional[str] = None
    citations: Optional[List[str]] = None
    escalated_to: Optional[str] = None
    history: List[Turn] = Field(default_factory=list)
    customer_profile: Optional[CustomerProfile] = None
    observations: List[AgentObservation] = Field(default_factory=list)
    complex_case_resolution: Optional[ComplexCaseResolution] = None
    tools_registry: Optional[dict[str, str]] = Field(default_factory=dict)
