from pydantic import BaseModel


class StaffUser(BaseModel):
    id: str
    email: str
    created_at: str
