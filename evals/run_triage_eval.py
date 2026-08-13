import os

from dotenv import load_dotenv
from langfuse import Langfuse

from models.llm_profile import default_non_thinking_model

os.environ['LITELLM_LOG'] = 'DEBUG'
from tasks import triage_task

load_dotenv()
langfuse = Langfuse()
prompt = langfuse.get_prompt("triage")

metadata = {
    "prompt": prompt.name,
    "prompt_version": str(prompt.version),
    "model": default_non_thinking_model.model
}

print(f"running triage eval for prompt version: {prompt.version}")

result = langfuse.run_experiment(
    name="triage-baseline",
    data=langfuse.get_dataset("triage-golden").items,
    task=triage_task,
    max_concurrency=32,
    metadata=metadata
)

print(result.format(include_item_results=True))
