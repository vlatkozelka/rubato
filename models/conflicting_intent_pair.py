from pydantic import BaseModel


class ConflictingIntentPair(BaseModel):
    """
    Two simple intents that can NEVER be resolved together automatically.
    If both appear present in one message, triage must return
    'complex_case', not 'composite' — the conflict requires reasoning
    (or clarification from the customer), not just running both handlers.
    """
    intent_a: str
    intent_b: str
    reason: str
