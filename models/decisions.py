from enum import Enum
from pydantic import BaseModel


class ComplexCaseDecision(str, Enum):
    EXCHANGE = "exchange"
    REFUND = "refund"
    PARTIAL_CREDIT = "partial_credit"
    DENIAL = "denial"


class ComplexCaseResolution(BaseModel):
    decision: ComplexCaseDecision
    order_id: str
    customer_reason: str   # normalized version of what the customer said, e.g. "broken zipper on arrival"
    reasoning: str          # agent's internal justification for the decision — supporting detail for the approver
    customer_message: str   # reply to send back to the customer