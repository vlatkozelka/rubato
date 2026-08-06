import re
from typing import Any, Optional

from models.customer import Customer

MASK = "[REDACTED]"


class PiiRedactor:
    """Exact-match redaction against the known customer record.

    Deliberately not a general PII/NER detector — it masks the current
    customer's own name/email if they appear in text about to be
    logged. Won't catch PII about someone else the customer mentions,
    or near-matches/typos. That trade-off is documented in
    DECISIONS.md; it's the pragmatic choice for a known, bound customer
    record rather than free-text entity detection.
    """

    def redact_text(self, text: Optional[str], customer: Optional[Customer]) -> Optional[str]:
        if text is None or customer is None:
            return text

        redacted = text
        if customer.email:
            redacted = redacted.replace(customer.email, MASK)
        if customer.name:
            redacted = re.sub(re.escape(customer.name), MASK, redacted, flags=re.IGNORECASE)
        return redacted

    def redact_value(self, value: Any, customer: Optional[Customer]) -> Any:
        """Recursively redact string leaves in a dict/list structure."""
        if customer is None:
            return value
        if isinstance(value, str):
            return self.redact_text(value, customer)
        if isinstance(value, dict):
            return {k: self.redact_value(v, customer) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact_value(v, customer) for v in value]
        return value