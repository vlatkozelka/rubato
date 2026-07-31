import logging

import instructor
from openai import OpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from app.timing import log_duration
from models.policy_answer import PolicyAnswer
from services.retrieval_service import retrieve_chunks

logger = logging.getLogger("rubato.services.policy_qa")

client = instructor.from_openai(
    OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
    mode=instructor.Mode.JSON_SCHEMA,
)

SYSTEM_PROMPT = """
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


def answer_policy_question(question: str, top_k: int = 3) -> PolicyAnswer:
    chunks = retrieve_chunks(question, top_k=top_k)

    excerpts = "\n\n".join(
        f"[{c.source}#{c.text.splitlines()[0].lstrip('# ').strip()}]\n{c.text}"
        for c in chunks
    )

    with log_duration(logger, "llm_call_finished", service="policy_qa_service", function="answer_policy_question"):
        return client.chat.completions.create(
            model=LLM_MODEL,
            response_model=PolicyAnswer,
            max_retries=3,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Policy excerpts:\n\n{excerpts}\n\nQuestion: {question}"},
            ],
        )