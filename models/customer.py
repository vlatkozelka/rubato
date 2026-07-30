from typing import Literal
from pydantic import BaseModel


class Customer(BaseModel):
    id: str
    name: str
    email: str
    tier: Literal["standard", "vip"]