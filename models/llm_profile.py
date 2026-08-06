from pydantic import BaseModel
from typing import Any

class LLMProfile(BaseModel):
    model: str
    api_base: str
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    min_p: float = 0.0
    presence_penalty: float = 1.5
    repetition_penalty: float = 1.0
    max_tokens: int = 1024
    chat_template_kwargs: dict[str, Any] = {}


LOCAL_LLM_BASE_URL = "http://localhost:1234/v1"
LOCAL_QWEN_3_MODEL = "hosted_vllm/RedHatAI/Qwen3.5-9B-quantized.w4a16"


PROFILES: dict[str, LLMProfile] = {
    "qwen3_non_thinking": LLMProfile(
        model=LOCAL_QWEN_3_MODEL,
        api_base=LOCAL_LLM_BASE_URL,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        min_p=0.0,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        chat_template_kwargs={"enable_thinking": False},
    ),
    "qwen3_thinking": LLMProfile(
        model=LOCAL_QWEN_3_MODEL,
        api_base=LOCAL_LLM_BASE_URL,
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        min_p=0.0,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        chat_template_kwargs={"enable_thinking": True},
    ),
}