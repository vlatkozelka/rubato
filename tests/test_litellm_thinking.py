from langchain_core.messages import HumanMessage

from models.llm_profile import PROFILES
from services.llm_factory import get_chat_model
import instructor
from litellm import completion
from pydantic import BaseModel

class Answer(BaseModel):
    result: str

client = instructor.from_litellm(completion)

def call_with_raw(profile_name: str):
    profile = PROFILES[profile_name]
    return client.chat.completions.create_with_completion(
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
        response_model=Answer,
        messages=[{"role": "user", "content": "What is 17 * 24? Think it through."}],
    )

_, raw_on = call_with_raw("qwen3_thinking")
msg = raw_on.choices[0].message
print("THINKING ON — reasoning_content:", getattr(msg, "reasoning_content", None))
print("THINKING ON — tool_calls:", msg.tool_calls)

_, raw_off = call_with_raw("qwen3_non_thinking")
msg2 = raw_off.choices[0].message
print("THINKING OFF — reasoning_content:", getattr(msg2, "reasoning_content", None))
print("THINKING OFF — tool_calls:", msg2.tool_calls)