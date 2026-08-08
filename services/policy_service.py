import asyncio
import logging

from app.timing import log_duration
from models.llm_profile import default_non_thinking_model
from models.policy_answer import PolicyAnswer
from models.refund_policy import RefundPolicy
from services.llm_factory import get_async_instructor_client
from langfuse import get_client as get_langfuse_client

logger = logging.getLogger("rubato.services.policy_qa")


async def answer_policy_question(question: str, excerpts: str) -> PolicyAnswer:
    langfuse_client = get_langfuse_client()
    langfuse_prompt = langfuse_client.get_prompt("policy/generic_policy_question")
    sys_prompt = langfuse_prompt.compile()
    client = get_async_instructor_client(default_non_thinking_model)

    with log_duration(logger, "llm_call_finished", service="policy_qa_service", function="answer_policy_question"):
        return await client(
            prompt=langfuse_prompt,
            response_model=PolicyAnswer,
            max_retries=3,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Policy excerpts:\n\n{excerpts}\n\nQuestion: {question}"},
            ],
        )


async def get_refund_policy(category: str, excerpts: str) -> RefundPolicy:
    langfuse_client = get_langfuse_client()
    langfuse_prompt = langfuse_client.get_prompt("policy/generic_policy_question")
    sys_prompt = langfuse_prompt.compile(category=category)

    client = get_async_instructor_client(default_non_thinking_model)
    question = f"return refund request for {category} items"
    with log_duration(logger, "llm_call_finished", service="policy_qa_service", function="get_refund_policy"):
        try:
            return await client(
                prompt=langfuse_prompt,
                response_model=RefundPolicy,
                max_retries=3,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Policy excerpts:\n\n{excerpts}\n\nQuestion: {question}"},
                ],
            )
        except asyncio.CancelledError:
            raise
