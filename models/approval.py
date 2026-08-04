from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ApprovalType(str, Enum):
    REFUND_REQUEST = "refund_request"


class ApprovalPayload(BaseModel):
    order_id: str
    reason: str
    amount: Optional[float] = None


class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    DENIED = "denied"


class Approval(BaseModel):
    id: UUID
    reason: str
    type: ApprovalType
    payload: ApprovalPayload
    status: ApprovalStatus
    customer_id: str
    created_at: str
    updated_at: str
