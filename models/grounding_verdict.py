from typing import Optional

from pydantic import BaseModel, Field


class GroundingVerdict(BaseModel):
    is_grounded: bool
    ungrounded_claim: Optional[str] = Field(
        default=None, description="The specific claim not backed by observations, if any"
    )
    corrected_message: str = Field(
        description="If grounded, the original customer_message unchanged. "
                     "If not grounded, a rewritten version that removes or "
                     "softens the unsupported claim while preserving everything else."
    )