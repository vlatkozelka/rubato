from pydantic import BaseModel


class RefundPolicy(BaseModel):
    allowed_duration: int
    policy: str
