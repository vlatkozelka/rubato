from enum import Enum
from typing import Optional

from openai import BaseModel


class InjectionSource(str, Enum):
    HEURISTIC = "heuristic"
    CLASSIFIER = "classifier"
    NONE = "none"



class InjectionCheckResult(BaseModel):
    flagged: bool
    source: InjectionSource
    reason: Optional[str] = None

from pydantic import BaseModel, Field


class InjectionClassification(BaseModel):
    is_injection: bool
    reason: str = Field(
        description="Brief explanation of why this message was or was not flagged"
    )