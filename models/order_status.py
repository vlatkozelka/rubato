# models/order_status.py
from typing import Literal, Union
from pydantic import BaseModel, Field


class ProcessingStatus(BaseModel):
    kind: Literal["processing"] = "processing"


class ShippedStatus(BaseModel):
    kind: Literal["shipped"] = "shipped"


class DeliveredStatus(BaseModel):
    kind: Literal["delivered"] = "delivered"
    delivered_at: str


class CancelledStatus(BaseModel):
    kind: Literal["cancelled"] = "cancelled"


OrderStatus = Union[ProcessingStatus, ShippedStatus, DeliveredStatus, CancelledStatus]
