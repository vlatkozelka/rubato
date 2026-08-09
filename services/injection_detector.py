import logging
import re
from typing import Optional

from langfuse import get_client as get_langfuse_client

from models.injection import InjectionCheckResult, InjectionSource, InjectionClassification
from models.llm_profile import default_non_thinking_model
from services.llm_factory import get_async_instructor_client

logger = logging.getLogger(__name__)

# (pattern, short reason name) — kept deliberately small and named, not
# exhaustive. Precision over recall: the classifier fallback exists to
# catch what these miss.
HEURISTIC_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all|any|the)?\s*(previous|prior|above)\s+instructions", "override_instructions"),
    (r"disregard\s+(all|any|the)?\s*(previous|prior|above)\s*(instructions|rules)", "override_instructions"),
    (r"forget\s+(everything|all)(\s+you\s+(were|have\s+been)\s+told)?", "override_instructions"),
    (r"new\s+instructions\s*:", "override_instructions"),
    (r"you\s+are\s+now\s+(a|an)\s+", "role_override"),
    (r"reveal\s+(your|the)\s+system\s+prompt", "prompt_extraction"),
    (r"(what|show)\s+(is|are|me)\s+your\s+(system\s+prompt|instructions)", "prompt_extraction"),
    (r"repeat\s+(the|your)\s+(instructions|prompt|rules)\s+(above|verbatim)", "prompt_extraction"),
]


class InjectionDetector:
    def __init__(self):
        self._compiled = [
            (re.compile(pattern, re.IGNORECASE), reason)
            for pattern, reason in HEURISTIC_PATTERNS
        ]
        self.client = get_async_instructor_client(default_non_thinking_model)

    def check_heuristics(self, message: str) -> Optional[str]:
        for pattern, reason in self._compiled:
            if pattern.search(message):
                return reason
        return None

    async def check_classifier(self, message: str) -> Optional[str]:
        langfuse_client = get_langfuse_client()
        langfuse_prompt = langfuse_client.get_prompt("security/injection_classifier")
        system_prompt = langfuse_prompt.compile()

        result = await self.client(
            prompt=langfuse_prompt,
            response_model=InjectionClassification,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
        )
        return result.reason if result.is_injection else None


    async def check(self, message: str) -> InjectionCheckResult:
        heuristic_reason = self.check_heuristics(message)
        if heuristic_reason:
            return InjectionCheckResult(
                flagged=True,
                source=InjectionSource.HEURISTIC,
                reason=heuristic_reason,
            )

        classifier_reason = await self.check_classifier(message)
        if classifier_reason:
            return InjectionCheckResult(
                flagged=True,
                source=InjectionSource.CLASSIFIER,
                reason=classifier_reason,
            )

        return InjectionCheckResult(flagged=False, source=InjectionSource.NONE)
