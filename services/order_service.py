import json
from typing import Optional

from app.config import DATA_DIR
from models.order import Order


def _load_orders() -> list[dict]:
    path = DATA_DIR / "orders.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_order_by_id(order_id: str) -> Optional[Order]:
    for raw in _load_orders():
        if raw["id"] == order_id:
            return Order(**raw)
    return None
