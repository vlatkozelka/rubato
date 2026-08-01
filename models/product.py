from typing import Optional

from pydantic import BaseModel


class Product(BaseModel):
    id: str
    name: str
    price: float
    category: str
    size: Optional[str] = None
    stock: int
