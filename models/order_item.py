from typing import Optional

from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: str
    name: str
    qty: int
    price: float
    size: Optional[str] = None
