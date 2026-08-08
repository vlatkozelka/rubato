from dotenv import load_dotenv

load_dotenv()

from models.llm_profile import default_non_thinking_model, groq_qwen_no_reasoning, groq_qwen_reasoning, \
    groq_gpt_oss_20_low_reasoning, groq_gpt_oss_20_high_reasoning

import asyncio

from services.llm_factory import get_async_instructor_client


async def test():
    sys_prompt = "You are a funny chatbot, your purpose is to entertain"
    profiles = [groq_gpt_oss_20_low_reasoning, groq_gpt_oss_20_high_reasoning]
    for profile in profiles:
        print(f"testing model: {profile.name}---->\n\n")
        client = get_async_instructor_client(profile)
        result = await client(
            response_model=None,
            max_retries=1,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "Tell me a joke"},
            ],
        )
        print("<----\nresult:")
        print(f"{result}\n\n\n")


if __name__ == "__main__":
    asyncio.run(test())
