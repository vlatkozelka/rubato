from functools import lru_cache
import logging
import instructor
from litellm import completion, acompletion
from langchain_litellm import ChatLiteLLM

from models.llm_profile import PROFILES

import litellm
from langfuse import get_client

litellm.success_callback = ["langfuse_otel"]
litellm.failure_callback = ["langfuse_otel"]

# litellm's OTel integration also tries to write gen_ai.* attributes onto
# whatever span was active when a call finishes, as a fire-and-forget
# background task — by the time it runs, our per-node span (see
# graph/instrumentation.py) has usually already closed. That write is
# harmless noise: the readable input/output we actually rely on is set
# synchronously via the generation span below, before it closes.
logging.getLogger("opentelemetry.sdk.trace").setLevel(logging.ERROR)


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
        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name=f"llm:{profile_name}",
            model=profile.model,
            input=kwargs.get("messages"),
        ) as generation:
            result = client.chat.completions.create(
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
            generation.update(output=result)
        return result

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
        langfuse = get_client()
        with langfuse.start_as_current_observation(
            as_type="generation",
            name=f"llm:{profile_name}",
            model=profile.model,
            input=kwargs.get("messages"),
        ) as generation:
            result = await client.chat.completions.create(
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
            generation.update(output=result)
        return result

    return create
