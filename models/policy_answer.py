from typing import List
from pydantic import BaseModel


class PolicyAnswer(BaseModel):
    answer: str
    cited_sources: List[str]  # e.g. ["return-policy.md#Opened software"]
    grounded: bool  # False if the retrieved chunks didn't actually contain an answer