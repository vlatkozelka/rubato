import asyncio
import random
import time
from openai import AsyncOpenAI

client = AsyncOpenAI(
    base_url="http://localhost:1234/v1",  # your vLLM endpoint
    api_key="not-needed",
)

MODEL = "RedHatAI/Qwen3.5-9B-quantized.w4a16"

FILLER_UNITS = [
    "Return window is 30 days from delivery for standard items. ",
    "Electronics have a 14-day return window, no exceptions. ",
    "Warranty claims for manufacturing defects are handled separately from returns. ",
    "Free return shipping applies above a $75 order threshold. ",
    "Opened software is non-returnable under any circumstance. ",
]

RUN_SEED = int(time.time())  # different every scripts execution

def build_prompt(case_id: int) -> str:
    # Deterministic-but-distinct shuffle per case so the prefix genuinely
    # differs from the start of the context, defeating prefix caching so
    # we measure real prefill cost instead of a cache-hit shortcut.
    rng = random.Random(RUN_SEED + case_id)
    shuffled = FILLER_UNITS.copy()
    rng.shuffle(shuffled)
    filler = "".join(shuffled) * 200  # tune multiplier to hit target token count

    return f"""You are a customer support agent. Use the policy context below
to answer the customer's question, citing the relevant clause.

POLICY CONTEXT:
{filler}

CUSTOMER MESSAGE (case {case_id}):
My order arrived 20 days ago and the jacket has a broken zipper.
Can I get a refund or exchange?

Answer concisely, citing the specific policy clause you relied on."""


async def run_case(case_id: int, semaphore: asyncio.Semaphore):
    async with semaphore:
        start = time.perf_counter()
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": build_prompt(case_id)}],
            max_tokens=300,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False}
            },
        )
        elapsed = time.perf_counter() - start
        usage = response.usage
        return {
            "case_id": case_id,
            "elapsed_s": round(elapsed, 2),
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
        }


async def main():
    semaphore = asyncio.Semaphore(4)  # matches --max-num-seqs 4
    start = time.perf_counter()

    results = await asyncio.gather(*(run_case(i, semaphore) for i in range(8)))

    total_elapsed = time.perf_counter() - start

    for r in sorted(results, key=lambda r: r["case_id"]):
        print(r)

    print(f"\nTotal wall time for 8 cases (concurrency=4): {total_elapsed:.2f}s")
    print(f"Avg per-case latency: {sum(r['elapsed_s'] for r in results) / len(results):.2f}s")


if __name__ == "__main__":
    asyncio.run(main())