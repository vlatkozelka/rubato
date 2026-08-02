from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CustomerProfile(BaseModel):
    customer_id: str
    refund_request_count: int
    last_contacted_at: Optional[datetime] = None
    notes: Optional[str] = None