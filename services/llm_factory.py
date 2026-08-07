from functools import lru_cache
import instructor
from litellm import completion, acompletion
from langchain_litellm import ChatLiteLLM

from models.llm_profile import PROFILES

import litellm
from langfuse import get_client

litellm.success_callback = ["langfuse_otel"]
litellm.failure_callback = ["langfuse_otel"]

import os
print(">>> OTEL_EXPORTER_OTLP_HEADERS at factory import:", os.environ.get("OTEL_EXPORTER_OTLP_HEADERS"))


def _require_active_trace():
    langfuse = get_client()
    if langfuse.get_current_trace_id() is None:
        raise RuntimeError(
            "LLM call attempted with no active Langfuse trace. "
            "This call must happen inside an @observe()-decorated function."
        )


@lru_cache(maxsize=None)
def get_instructor_client(profile_name: str):
    profile = PROFILES[profile_name]
    client = instructor.from_litellm(completion)

    def create(**kwargs):
        # _require_active_trace()
        return client.chat.completions.create(
            model=profile.model,
            api_base=profile.api_base,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
            top_p=profile.top_p,
            top_k=profile.top_k,
            min_p=profile.min_p,
            presence_penalty=profile.presence_penalty,
            repetition_penalty=profile.repetition_penalty,
            chat_template_kwargs=profile.chat_template_kwargs,
            **kwargs,
        )

    return create


@lru_cache(maxsize=None)
def get_chat_model(profile_name: str) -> ChatLiteLLM:
    # _require_active_trace()
    profile = PROFILES[profile_name]
    return ChatLiteLLM(
        model=profile.model,
        api_base=profile.api_base,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        model_kwargs={
            "top_p": profile.top_p,
            "top_k": profile.top_k,
            "min_p": profile.min_p,
            "presence_penalty": profile.presence_penalty,
            "repetition_penalty": profile.repetition_penalty,
            "chat_template_kwargs": profile.chat_template_kwargs,
        },
    )


@lru_cache(maxsize=None)
def get_async_instructor_client(profile_name: str):
    profile = PROFILES[profile_name]
    client = instructor.from_litellm(acompletion)

    async def create(**kwargs):
        # _require_active_trace()
        return await client.chat.completions.create(
            model=profile.model,
            api_base=profile.api_base,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
            top_p=profile.top_p,
            top_k=profile.top_k,
            min_p=profile.min_p,
            presence_penalty=profile.presence_penalty,
            repetition_penalty=profile.repetition_penalty,
            chat_template_kwargs=profile.chat_template_kwargs,
            **kwargs,
        )

    return create
