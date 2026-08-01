from typing import Optional

from pydantic import BaseModel

from models.user_role import UserRole


class AuthPrincipal(BaseModel):
    """The identity decoded from a validated JWT, injected into route handlers."""
    sub: str
    role: UserRole
    customer_id: Optional[str] = None
