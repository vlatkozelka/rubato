from typing import List

from pydantic import BaseModel, model_validator

from models.order_item import OrderItem
from models.order_status import OrderStatus


class Order(BaseModel):
    id: str
    customer_id: str
    items: List[OrderItem]
    status: OrderStatus
    date: str
    total: float

    @model_validator(mode="before")
    @classmethod
    def _nest_status(cls, data: dict) -> dict:
        """
        Raw orders.json is flat: {"status": "delivered", "delivered_at": "...", ...}.
        Reshape into the discriminated union's expected form before validation:
        {"status": {"kind": "delivered", "delivered_at": "..."}, ...}.
        """
        data = dict(data)  # don't mutate the caller's dict
        raw_status = data.pop("status")
        delivered_at = data.pop("delivered_at", None)

        if raw_status == "delivered":
            data["status"] = {"kind": "delivered", "delivered_at": delivered_at}
        else:
            data["status"] = {"kind": raw_status}

        return data
