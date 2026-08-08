from dotenv import load_dotenv

load_dotenv()

from models.llm_profile import default_non_thinking_model, default_thinking_model

import asyncio

from models.triage_result import TriageResult
from services.llm_factory import get_async_instructor_client


async def test():
    sys_prompt = """
    You are a triage classifier for an e-commerce support inbox. Classify each
customer message into exactly one intent and extract any order ID, product
reference, and sentiment expressed.

Intents:
- order_status: asking where an order is, or its delivery state.
- policy_question: asking ABOUT a policy (windows, fees, rules) — a question, not a request to act.
- return_request: asking to send an item back (for exchange, store credit, or as a step toward a refund).
- refund_request: asking for money back to the original payment method.
- price_check: asking the price, cost, or fee of a specific product — a question about cost, not about policy rules or an order.
- escalate: asking for a human/manager, or saying the bot isn't helping.
- chitchat: greetings, small talk, or messages with no support-related content.
- complex_case: covers two situations — (a) the correct resolution cannot
  be determined from the message alone and requires looking up facts
  (order history, return history, stock) before knowing what applies, or
  (b) the message contains two or more simple intents (order_status,
  policy_question, return_request, refund_request), whether they are
  independent or conflicting.

Conversation history, if present, appears as prior turns before the current
message. Use it to resolve what the current message means — a short reply
like an order ID, a "yes", or a bare number is often an answer to a question
YOU (the assistant) just asked, not a new unrelated request. Classify the
CURRENT message's intent in light of that context. For example, if your
last turn asked "which order would you like refunded?" and the current
message is just an order number, classify it as refund_request, using the
order ID from the current message, informed by what was being resolved in
the prior turn.

Examples:

1. "How many days do I have to return something if I changed my mind?"
   -> policy_question (a question about the window, not a request to act now)

2. "I'd like to return the jacket, wrong size."
   -> return_request (an actual request to act)

3. "Where's my order, and what's your return policy if it arrives broken?"
   -> complex_case
   (two independent, non-conflicting asks — both need answering, which
   a single terminal node can't do)

4. "I want a refund for this jacket, but if that's not possible I'd rather just exchange it."
   -> complex_case
   (conflicting outcomes for the same item — cannot resolve without a decision)

5. "hey"
   -> chitchat (no support content to classify)

6. "The jacket I got last week arrived with a broken zipper, and I already returned something last month. What can you do?"
   -> complex_case
   (no second simple intent stated — resolution depends on facts not in the message: defect verification, return history, stock)

7. "What's the price of the yoga mat, and can I return a jacket I bought 20 days ago?"
   -> complex_case
   (independent asks — a cost lookup and a return request, no conflict, but still two intents)

8. History: [user: "I want a refund", assistant: "Sure, which order would you like refunded?"]
   Current message: "ord_001"
   -> refund_request, order_id="ord_001"
   (a bare order number alone would normally look like order_status, but
   given the prior turn was the assistant asking which order to refund,
   this is a continuation of that refund flow)   
   
Always extract order_id and product_reference if present. Set sentiment from
the customer's actual tone (neutral, frustrated, angry) — never let intent
classification influence the sentiment field.
    
    
    """
    client = get_async_instructor_client(default_non_thinking_model)
    result = await client(
        response_model=None,
        max_retries=3,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": "What is the warranty on electronics?"},
        ],
    )
    print(f"result: {result}")

    client = get_async_instructor_client(default_thinking_model)
    result = await client(
        response_model=None,
        max_retries=3,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": "What is the warranty on electronics?"},
        ],
    )
    print(f"result: {result}")


if __name__ == "__main__":
    asyncio.run(test())
