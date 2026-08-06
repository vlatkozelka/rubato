import asyncio
import sys

from services.policy_service import answer_policy_question


async def _test():
    messages = [
        "How many days do I have to return an opened software license?",
        "My jacket arrived defective, how long do I have to report it?",
        "Do you offer gift wrapping?",
        "What is the refund policy window for electronics like fitness trackers?"
    ]

    for message in messages:
        print(f"{message}\n")
        result = await answer_policy_question(message, 3)
        print(f"{result}\n\n\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(_test())
