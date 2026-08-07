import asyncio
import logging

from app.timing import log_duration
from models.policy_answer import PolicyAnswer
from models.refund_policy import RefundPolicy
from services.llm_factory import get_async_instructor_client

logger = logging.getLogger("rubato.services.policy_qa")

async def answer_policy_question(question: str, excerpts: str) -> PolicyAnswer:

    client = get_async_instructor_client("qwen3_non_thinking")

    prompt = """
    You are a policy assistant for an e-commerce store. Answer the customer's
    question using ONLY the policy excerpts provided below. Do not use any
    outside knowledge.

    Rules:
    - Every claim in your answer must be traceable to one of the excerpts.
    - cited_sources must list which excerpt(s) you actually used, formatted as
      "filename#section-header".

    Example 1 — excerpts don't cover the question:
    Question: "Do you offer gift wrapping?"
    Correct answer: "I don't have information on gift wrapping in our policies.
    I'd recommend checking with support directly for that."
    cited_sources=[], grounded=false
    (Note: nothing about VIP programs, shipping, or other unrelated policies is
    mentioned, even though they were retrieved.)

    Example 2 — two excerpts conflict:
    Excerpt A says defective items have a 30-day window. Excerpt B says
    warranty covers defects for 90 days.
    Correct answer: "Our policies actually disagree here — one document says
    30 days for defective items, another says 90 days under warranty. I don't
    want to give you the wrong window, so I'd recommend confirming with a
    support agent directly."
    cited_sources=[both sources], grounded=true
    (Note: the answer does NOT try to explain how both apply, does NOT pick
    one as more correct, and does NOT describe them as complementary. It
    states the disagreement as the finding and defers to a human.)

    Follow the exact style of these two examples when the same situation
    arises: keep the "don't have this info" answer brief and free of
    unrelated details, and keep the conflict answer focused on naming the
    disagreement rather than resolving it.
    """

    with log_duration(logger, "llm_call_finished", service="policy_qa_service", function="answer_policy_question"):
        return await client(
            response_model=PolicyAnswer,
            max_retries=3,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Policy excerpts:\n\n{excerpts}\n\nQuestion: {question}"},
            ],
        )


async def get_refund_policy(category: str, excerpts: str) -> RefundPolicy:
    client = get_async_instructor_client("qwen3_non_thinking")
    question = f"return refund request for {category} items"
    prompt = f"""
    You are a policy lookup assistant for an e-commerce support system.

You will be given a product category and a set of retrieved policy document
excerpts. Your job is to determine the applicable refund/return window for
that category, based ONLY on the provided excerpts.

Rules:
- allowed_duration must be the number of days a customer has to request a
  refund for an item in this category, according to the excerpts.
- policy must be a short explanation of which rule applies and why, citing
  the specific policy document it came from (e.g. "return-policy.md" or
  "warranty.md").
- If the excerpts contain conflicting windows for this category (e.g. a
  general return window vs. a separate defective-item warranty window),
  do not silently pick one. Set allowed_duration to the LONGER of the two
  windows, and explain the conflict explicitly in the policy field so a
  human reviewer is aware both rules exist.
- If no relevant policy is found in the excerpts, set allowed_duration to 0
  and explain in policy that no matching policy was found.
- Do not invent a duration that is not stated in the excerpts.

Category: {category}
"""
    with log_duration(logger, "llm_call_finished", service="policy_qa_service", function="get_refund_policy"):
        try:
            return await client(
                response_model=RefundPolicy,
                max_retries=3,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Policy excerpts:\n\n{excerpts}\n\nQuestion: {question}"},
                ],
            )
        except asyncio.CancelledError:
            raise
