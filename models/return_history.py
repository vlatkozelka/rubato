from typing import Literal

from pydantic import BaseModel

ReturnReason = Literal["changed_mind", "wrong_size", "defective", "other"]
ReturnResolution = Literal["refunded", "exchanged", "denied"]


class ReturnHistoryEntry(BaseModel):
    id: int
    customer_id: str
    order_id: str
    product_id: str
    reason: ReturnReason
    requested_at: str
    resolution: ReturnResolution
    amount: float
