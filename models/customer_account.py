from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CustomerAccount(BaseModel):
    id: str
    email: str
    tier: Literal["standard", "vip"]
    refund_request_count: int
    last_contacted_at: Optional[datetime] = None
