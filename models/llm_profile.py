import os
from enum import Enum
from abc import ABC, abstractmethod
from typing import Any, Optional, Union
from dataclasses import dataclass

from sympy import true


class Model(str, Enum):
    """Enum of all available models. Source of truth for model identities."""

    QWEN_3_5_9B = "hosted_vllm/RedHatAI/Qwen3.5-9B-quantized.w4a16"

    OPENROUTER_FREE = "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

    GROQ_LLAMA_70B = "groq/llama-3.3-70b-versatile"
    GROQ_GPT_OSS_120 = "groq/openai/gpt-oss-120b"
    GROQ_GPT_OSS_20 = "groq/openai/gpt-oss-20b"
    GROQ_QWEN_27_B = "groq/qwen/qwen3.6-27b"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"


class ModelProfile(ABC):
    """Base class for model profiles."""
    name: str
    model: Model
    api_base: str
    api_key: Optional[str] = None

    @abstractmethod
    def to_request_kwargs(self) -> dict[str, Any]:
        pass

    @staticmethod
    def _omit_none(**kwargs: Any) -> dict[str, Any]:
        return {k: v for k, v in kwargs.items() if v is not None}


@dataclass(frozen=True)
class LocalVLLMProfile(ModelProfile):
    name: str
    model: Model
    api_base: str = "http://localhost:1234/v1"
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    min_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    repetition_penalty: Optional[float] = None
    max_tokens: Optional[int] = None
    reasoning: Optional[bool] = None  # -> chat_template_kwargs["enable_thinking"]

    def to_request_kwargs(self) -> dict[str, Any]:
        chat_template_kwargs = {}
        if self.reasoning is not None:
            chat_template_kwargs["enable_thinking"] = self.reasoning

        return self._omit_none(
            model=self.model,
            api_base=self.api_base,
            api_key=self.api_key,
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            min_p=self.min_p,
            presence_penalty=self.presence_penalty,
            repetition_penalty=self.repetition_penalty,
            max_tokens=self.max_tokens,
            chat_template_kwargs=chat_template_kwargs or None,
        )


@dataclass(frozen=True)
class OpenRouterProfile(ModelProfile):
    name: str
    model: Model
    api_base="https://openrouter.ai/api/v1"
    api_key=os.environ["OPEN_ROUTER_API_KEY"]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reasoning: Optional[bool] = None  # -> {"reasoning": {"enabled": ...}}
    vendor_params: Optional[dict[str, Any]] = None

    def to_request_kwargs(self) -> dict[str, Any]:
        kwargs = self._omit_none(
            model=self.model,
            api_base=self.api_base,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if self.vendor_params:
            kwargs.update(self.vendor_params)
        if self.reasoning is not None:
            # merge rather than clobber, in case vendor_params also set "reasoning"
            reasoning_block = dict(kwargs.get("reasoning", {}))
            reasoning_block["enabled"] = self.reasoning
            kwargs["reasoning"] = reasoning_block
        return kwargs


@dataclass(frozen=True)
class ClaudeAPIProfile(ModelProfile):
    name: str
    model: Model
    api_base: str = "https://api.anthropic.com/v1"
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reasoning: Optional[bool] = None  # -> {"thinking": {"type": ..., "budget_tokens": ...}}
    thinking_budget_tokens: int = 1024

    def to_request_kwargs(self) -> dict[str, Any]:
        kwargs = self._omit_none(
            model=self.model,
            api_base=self.api_base,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if self.reasoning is not None:
            kwargs["thinking"] = (
                {"type": "enabled", "budget_tokens": self.thinking_budget_tokens}
                if self.reasoning
                else {"type": "disabled"}
            )
        return kwargs

@dataclass(frozen=True)
class GroqProfile(ModelProfile):
    name: str
    model: Model
    api_base="https://api.groq.com/openai/v1"
    api_key=os.environ.get("GROQ_API_KEY")
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reasoning_effort: Optional[str] = None  # "low"/"medium"/"high" or "none"/"default", model-dependent — caller's responsibility to match the right set
    reasoning_format: Optional[str] = "parsed"
    def to_request_kwargs(self) -> dict[str, Any]:
        return self._omit_none(
            model=self.model.value,
            api_base=self.api_base,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            allowed_openai_params=['reasoning_effort'],
            reasoning_effort=self.reasoning_effort,
            reasoning_format=self.reasoning_format
        )


qwen3_non_thinking = LocalVLLMProfile(
    name="qwen_3_non_thinking",
    model=Model.QWEN_3_5_9B,
    temperature=0.7,
    top_p=0.8,
    reasoning=False,
)

qwen3_thinking = LocalVLLMProfile(
    name="qwen_3_thinking",
    model=Model.QWEN_3_5_9B,
    temperature=1.0,
    top_p=0.95,
    reasoning=True,
)

openrouter_free_non_thinking = OpenRouterProfile(
    name="open_router_free_non_thinking",
    model=Model.OPENROUTER_FREE,
    reasoning=False,
)

openrouter_free_thinking = OpenRouterProfile(
    name="open_router_free_thinking",
    model=Model.OPENROUTER_FREE,
    reasoning=True
)

groq_llama_70b_low_reasoning = GroqProfile(
    name="groq_llama_70b_low_reasoning",
    model=Model.GROQ_LLAMA_70B
)


groq_llama_70b_high_reasoning = GroqProfile(
    name="groq_llama_70b_high_reasoning",
    model=Model.GROQ_LLAMA_70B
)



groq_gpt_oss_120_low_reasoning = GroqProfile(
    name="groq_gpt_oss_120_low_reasoning",
    model=Model.GROQ_GPT_OSS_120,
    reasoning_effort="low"
)

groq_gpt_oss_120_high_reasoning = GroqProfile(
    name="groq_gpt_oss_120_high_reasoning",
    model=Model.GROQ_GPT_OSS_120,
    reasoning_effort="medium"
)

groq_gpt_oss_20_low_reasoning = GroqProfile(
    name="groq_gpt_oss_120_low_reasoning",
    model=Model.GROQ_GPT_OSS_20,
    reasoning_effort="low"
)

groq_gpt_oss_20_high_reasoning = GroqProfile(
    name="groq_gpt_oss_120_high_reasoning",
    model=Model.GROQ_GPT_OSS_20,
    reasoning_effort="medium"
)

groq_qwen_no_reasoning = GroqProfile(
    name="groq_qwen_3_6_no_reasoning",
    model=Model.GROQ_QWEN_27_B,
    reasoning_effort="none"
)

groq_qwen_reasoning = GroqProfile(
    name="groq_qwen_3_6_reasoning",
    model=Model.GROQ_QWEN_27_B,
    reasoning_effort="default"
)

default_non_thinking_model = groq_gpt_oss_20_low_reasoning
default_thinking_model = groq_gpt_oss_20_high_reasoning

#claude_sonnet = ClaudeAPIProfile(model=Model.CLAUDE_3_5_SONNET)
#claude_haiku = ClaudeAPIProfile(model=Model.CLAUDE_3_5_HAIKU)

LLMProfile = Union[LocalVLLMProfile, OpenRouterProfile, ClaudeAPIProfile, GroqProfile]
