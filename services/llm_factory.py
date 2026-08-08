import logging
from functools import lru_cache
from typing import Optional, List

import instructor
import litellm
from instructor import Mode
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langfuse import get_client
from langfuse.model import PromptClient
from litellm import acompletion
from pydantic import BaseModel

from models.llm_profile import LLMProfile

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
def get_agent_client(profile: LLMProfile):
    # _require_active_trace()

    async def ainvoke(messages: List[BaseMessage],
                      tools: List[BaseTool],
                      system_prompt: str,
                      tool_strategy: ToolStrategy,
                      prompt: Optional[PromptClient] = None):
        langfuse = get_client()
        with langfuse.start_as_current_observation(
                as_type="generation",
                name=profile.name,
                model=profile.model,
                input=messages,
                prompt=prompt
        ) as generation:
            model = ChatLiteLLM(
                model=profile.model,
                api_base=profile.api_base,
                temperature=profile.temperature,
                max_tokens=profile.max_tokens,
                api_key=profile.api_key,
                model_kwargs=profile.to_request_kwargs(),
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
def get_async_instructor_client(llm_profile: LLMProfile):
    client = instructor.from_litellm(acompletion, mode=Mode.JSON)

    async def create(response_model: BaseModel, messages: List[BaseMessage], prompt: Optional[PromptClient] = None, max_retries: int = 3):
        # _require_active_trace()
        langfuse = get_client()
        with langfuse.start_as_current_observation(
                as_type="generation",
                name=llm_profile.name,
                model=llm_profile.model,
                input=messages,
                prompt=prompt
        ) as generation:
            result = await client.chat.completions.create(
                response_model=response_model,
                messages = messages,
                max_retries = max_retries,
                **llm_profile.to_request_kwargs()
            )
            generation.update(output=result)
        return result

    return create
