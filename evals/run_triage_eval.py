import os

from dotenv import load_dotenv
from langfuse import Langfuse
os.environ['LITELLM_LOG'] = 'DEBUG'
from tasks import triage_task

load_dotenv()
langfuse = Langfuse()

result = langfuse.run_experiment(
    name="triage-baseline-v1",
    data=langfuse.get_dataset("triage-golden").items,
    task=triage_task,
    max_concurrency=1
)

print(result.format())