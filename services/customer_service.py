import json
from typing import Optional

from app.config import DATA_DIR
from models.customer import Customer


def _load_customers() -> list[dict]:
    path = DATA_DIR / "customers.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_customer_by_id(customer_id: str) -> Optional[Customer]:
    for raw in _load_customers():
        if raw["id"] == customer_id:
            return Customer(**raw)
    return None
