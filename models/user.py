from typing import Optional

from pydantic import BaseModel

from models.user_role import UserRole


class User(BaseModel):
    id: str
    email: str
    role: UserRole
    customer_id: Optional[str] = None
    created_at: str
