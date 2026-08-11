from dotenv import load_dotenv

load_dotenv()
import json
from langfuse import Langfuse

langfuse = Langfuse()  # reads your existing LANGFUSE_* env vars, already configured

with open("evals/fixtures/golden_cases.json") as f:
    data = json.load(f)

DATASET_NAMES = ["triage-golden", "policy-qa-golden"]
for name in DATASET_NAMES:
    langfuse.create_dataset(name=name)


for case in data["cases"]:
    for dataset_name in case["datasets"]:
        langfuse.create_dataset_item(
            dataset_name=dataset_name,
            input={"message": case["message"], "customer_id": case["customer_id"], "order_id": case["order_id"]},
            expected_output={"intent": case["expected_intent"]},
            metadata={"case_id": case["case_id"]},
        )

print("done")