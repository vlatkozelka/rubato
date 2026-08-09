from dotenv import load_dotenv

load_dotenv()

from models.llm_profile import qwen3_non_thinking, qwen3_thinking

import asyncio

from services.llm_factory import get_async_instructor_client


async def test():
    sys_prompt = "You are a funny chatbot, your purpose is to entertain"
    profiles = [qwen3_non_thinking, qwen3_thinking]
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
