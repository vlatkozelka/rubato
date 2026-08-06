from functools import lru_cache
import instructor
from litellm import completion, acompletion
from langchain_litellm import ChatLiteLLM

from models.llm_profile import PROFILES


@lru_cache(maxsize=None)
def get_instructor_client(profile_name: str):
    profile = PROFILES[profile_name]
    client = instructor.from_litellm(completion)

    def create(**kwargs):
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