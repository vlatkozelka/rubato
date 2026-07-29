import instructor
from openai import OpenAI

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
from models.triage_result import TriageResult

client = instructor.from_openai(
    OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
    mode=instructor.Mode.JSON_SCHEMA,
)

def triage_message(message: str) -> TriageResult:
    return client.chat.completions.create(
        model=LLM_MODEL,
        response_model=TriageResult,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a triage classifier for an e-commerce support "
                    "inbox. Classify the customer's message into exactly one "
                    "intent and extract any order ID, product reference, and "
                    "sentiment expressed."
                ),
            },
            {"role": "user", "content": message},
        ],
    )
