from typing import List

from pydantic import BaseModel


class OrderSummary(BaseModel):
    order_id: str
    placed_at: str
    status: str
    total: float
    item_names: List[str]
