from dataclasses import Field
from functools import lru_cache
import logging
from typing import Optional, List

import instructor
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langfuse.model import PromptClient
from litellm import completion, acompletion
from langchain_litellm import ChatLiteLLM
from typer import Argument

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
def get_agent_client(profile_name: str):
    # _require_active_trace()
    profile = PROFILES[profile_name]

    async def ainvoke(messages: List[BaseMessage],
                      tools: List[BaseTool],
                      system_prompt: str,
                      tool_strategy: ToolStrategy,
                      prompt: Optional[PromptClient] = None):
        langfuse = get_client()
        with langfuse.start_as_current_observation(
                as_type="generation",
                name=f"llm:{profile_name}",
                model=profile.model,
                input=messages,
                prompt=prompt
        ) as generation:
            model = ChatLiteLLM(
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
            agent = create_agent(
                model=model,
                tools=tools,
                system_prompt=system_prompt,
                response_format=tool_strategy,
            )
            result = await agent.ainvoke({"messages": messages},
                                   config=RunnableConfig(recursion_limit=15),
                                   )
            generation.update(output=result)
        return result

    return ainvoke


@lru_cache(maxsize=None)
def get_async_instructor_client(profile_name: str):
    profile = PROFILES[profile_name]
    client = instructor.from_litellm(acompletion)

    async def create(prompt: Optional[PromptClient] = None, **kwargs):
        # _require_active_trace()
        langfuse = get_client()
        with langfuse.start_as_current_observation(
                as_type="generation",
                name=f"llm:{profile_name}",
                model=profile.model,
                input=kwargs.get("messages"),
                prompt=prompt
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
