from dotenv import load_dotenv

load_dotenv()

from models.llm_profile import qwen3_non_thinking, qwen3_thinking, claude_haiku, default_non_thinking_model, \
    default_thinking_model

import asyncio

from services.llm_factory import get_async_instructor_client


async def test():
    sys_prompt = "You are a funny chatbot, your purpose is to entertain"
    profiles = [default_non_thinking_model, default_thinking_model]
    for profile in profiles:
        print(f"testing model: {profile.name}---->\n")
        client = get_async_instructor_client(profile)
        result = await client(
            response_model=None,
            max_retries=1,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "Tell me a joke"},
            ],
        )
        print("<----\nresult\n:")
        print(f"{result}\n")


if __name__ == "__main__":
    asyncio.run(test())
