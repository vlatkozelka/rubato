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

from langgraph.errors import GraphRecursionError
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage


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



logger = logging.getLogger("LLM")


class AgentTraceCallback(AsyncCallbackHandler):
    """Logs each turn of the ReAct loop so it's not a black box anymore."""

    def __init__(self):
        self.turn = 0

    async def on_chat_model_start(self, serialized, messages, **kwargs):
        self.turn += 1
        logger.info(f"[turn {self.turn}] model call start")

    async def on_llm_end(self, response, **kwargs):
        usage = None
        try:
            usage = response.llm_output.get("token_usage")
        except Exception:
            pass
        tool_calls = []
        try:
            for gen in response.generations[0]:
                msg = getattr(gen, "message", None)
                if msg is not None and getattr(msg, "tool_calls", None):
                    tool_calls = [tc["name"] for tc in msg.tool_calls]
        except Exception:
            pass
        logger.info(f"[turn {self.turn}] model call end, usage={usage}, tool_calls={tool_calls}")

    async def on_tool_start(self, serialized, input_str, **kwargs):
        logger.info(f"[turn {self.turn}] tool start: {serialized.get('name')} input={input_str}")

    async def on_tool_end(self, output, **kwargs):
        logger.info(f"[turn {self.turn}] tool end: {str(output)[:500]}")

    async def on_tool_error(self, error, **kwargs):
        logger.warning(f"[turn {self.turn}] tool error: {error}")


@lru_cache(maxsize=None)
def get_agent_client(profile: LLMProfile):
    # _require_active_trace()

    async def ainvoke(messages: List[BaseMessage],
                      tools: List[BaseTool],
                      system_prompt: str,
                      tool_strategy: ToolStrategy,
                      prompt: Optional[PromptClient] = None,
                      recursion_limit: int = 15):
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
                model_kwargs={
                    **profile.to_request_kwargs(),
                    "tool_choice": "auto",  # explicit instead of relying on LangChain's default translation
                },
            )
            agent = create_agent(
                model=model,
                tools=tools,
                system_prompt=system_prompt,
                response_format=tool_strategy,
            )

            callback = AgentTraceCallback()
            try:
                result = await agent.ainvoke(
                    {"messages": messages},
                    config=RunnableConfig(
                        recursion_limit=recursion_limit,
                        callbacks=[callback],
                    ),
                )
            except GraphRecursionError:
                logger.error(
                    f"agent hit recursion_limit={recursion_limit} without terminating "
                    f"(model={profile.model}); likely failed to emit the structured-response tool call"
                )
                generation.update(level="ERROR", status_message="recursion_limit exceeded")
                raise

            # usage comes from each AIMessage in the loop, not a single _raw_response
            ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.usage_metadata]
            usage_details = {
                "input_tokens": sum(m.usage_metadata.get("input_tokens", 0) for m in ai_messages),
                "output_tokens": sum(m.usage_metadata.get("output_tokens", 0) for m in ai_messages),
                "total_tokens": sum(m.usage_metadata.get("total_tokens", 0) for m in ai_messages),
            }
            generation.update(output=result, usage_details=usage_details or None)

        return result

    return ainvoke


@lru_cache(maxsize=None)
def get_async_instructor_client(llm_profile: LLMProfile):
    client = instructor.from_litellm(acompletion, mode=Mode.JSON_SCHEMA)

    async def create(response_model: BaseModel, messages: List[BaseMessage], prompt: Optional[PromptClient] = None,
                     max_retries: int = 3):
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
                messages=messages,
                max_retries=max_retries,
                **llm_profile.to_request_kwargs()
            )
            try:
                generation.update(output=result, usage_details=result._raw_response.usage)
            except AttributeError:
                generation.update(output=result)
        return result

    return create
