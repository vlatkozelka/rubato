import logging

from app.timing import log_duration
from models.llm_profile import default_non_thinking_model
from models.triage_result import TriageResult
from services.llm_factory import get_async_instructor_client
from langfuse import get_client as get_langfuse_client

logger = logging.getLogger("rubato.services.triage")

from models.turn import Turn


async def triage_message(message: str, history: list[Turn] | None = None) -> TriageResult:
    langfuse_client = get_langfuse_client()
    langfuse_prompt = langfuse_client.get_prompt("triage")
    system_prompt = langfuse_prompt.compile()
    llm_client = get_async_instructor_client(default_non_thinking_model)

    history_messages = [
        {"role": "user" if t.role == "user" else "assistant", "content": t.content}
        for t in (history or [])
    ]

    with log_duration(logger, "llm_call_finished", service="triage_service", function="triage_message"):
        return await llm_client(
            prompt=langfuse_prompt,
            response_model=TriageResult,
            max_retries=3,
            messages=[
                {"role": "system", "content": system_prompt},
                *history_messages,
                {"role": "user", "content": message},
            ],
        )
