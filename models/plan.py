from pydantic import BaseModel



class PlanStep(BaseModel):
    step_id: int
    description: str          # e.g. "Look up the customer's recent orders"
    tool_hint: str | None = None  # e.g. "get_orders_by_customer" - a hint, not binding

class Plan(BaseModel):
    steps: list[PlanStep]


class PlanStepArgs(BaseModel):
    args: dict