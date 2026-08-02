from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime