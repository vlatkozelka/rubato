import instructor
from openai import OpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from models.triage_result import TriageResult
from models.conflicting_intent_pair import ConflictingIntentPair

client = instructor.from_openai(
    OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
    mode=instructor.Mode.JSON_SCHEMA,
)

CONFLICTING_INTENT_PAIRS: list[ConflictingIntentPair] = [
    ConflictingIntentPair(
        intent_a="refund_request",
        intent_b="return_request",
        reason=(
            "Money back and a return-for-exchange/replacement are "
            "mutually exclusive resolutions for the same item — the "
            "customer must end up with one outcome, not both."
        ),
    ),
]


def _format_conflict_pairs() -> str:
    return "\n".join(
        f"- {p.intent_a} + {p.intent_b}: {p.reason}"
        for p in CONFLICTING_INTENT_PAIRS
    )


SYSTEM_PROMPT = f"""
You are a triage classifier for an e-commerce support inbox. Classify each
customer message into exactly one intent and extract any order ID, product
reference, and sentiment expressed.

Intents:
- order_status: asking where an order is, or its delivery state.
- policy_question: asking ABOUT a policy (windows, fees, rules) — a question, not a request to act.
- return_request: asking to send an item back (for exchange, store credit, or as a step toward a refund).
- refund_request: asking for money back to the original payment method.
- escalate: asking for a human/manager, or saying the bot isn't helping.
- chitchat: greetings, small talk, or messages with no support-related content.
- composite: the message contains TWO OR MORE of [order_status, policy_question, return_request, refund_request], and they are INDEPENDENT — each resolves on its own without affecting the other.
- complex_case: the correct resolution cannot be determined from the message alone — it requires looking up facts (order history, return history, stock) before knowing what applies. This includes any message where two sub-intents CONFLICT rather than coexist.

Known conflicting intent pairs — if a message contains BOTH sides of one of
these, classify as complex_case, never composite:
{_format_conflict_pairs()}

Whenever more than one simple intent (order_status, policy_question,
return_request, refund_request) is present in the message — whether they
are independent (composite) or conflicting (complex_case) — list every one
you detected in sub_intents. Leave sub_intents empty when only one intent
is present, including for chitchat, escalate, and single-cause
complex_case (e.g. a case needing lookup but with no second intent stated).

Examples:

1. "How many days do I have to return something if I changed my mind?"
   -> policy_question (a question about the window, not a request to act now)

2. "I'd like to return the jacket, wrong size."
   -> return_request (an actual request to act)

3. "Where's my order, and what's your return policy if it arrives broken?"
   -> composite, sub_intents=[order_status, policy_question]
   (independent, non-conflicting asks — answer both)

4. "I want a refund for this jacket, but if that's not possible I'd rather just exchange it."
   -> complex_case, sub_intents=[refund_request, return_request]
   (conflicting outcomes for the same item — cannot resolve without a decision)

5. "hey"
   -> chitchat (no support content to classify, sub_intents empty)

6. "The jacket I got last week arrived with a broken zipper, and I already returned something last month. What can you do?"
   -> complex_case, sub_intents empty
   (no second simple intent stated — resolution depends on facts not in the message: defect verification, return history, stock)

Always extract order_id and product_reference if present. Set sentiment from
the customer's actual tone (neutral, frustrated, angry) — never let intent
classification influence the sentiment field.
""".strip()


def triage_message(message: str) -> TriageResult:
    return client.chat.completions.create(
        model=LLM_MODEL,
        response_model=TriageResult,
        max_retries=3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
    )
