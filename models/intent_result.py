from typing import List, Optional

from pydantic import BaseModel

from models.intent import Intent


class IntentResult(BaseModel):
    intent: Intent
    result: Optional[str] = None
    citations: Optional[List[str]] = None
