import logging
logging.basicConfig(level=logging.DEBUG)
from dotenv import load_dotenv
load_dotenv()


import os
os.environ["LANGFUSE_DEBUG"] = "True"

from langfuse import get_client

langfuse = get_client()

assert langfuse.auth_check(), "Langfuse auth failed"

with langfuse.start_as_current_observation(as_type="span", name="smoke-test-span") as span:
    span.update(input={"question": "does this actually work"}, output={"answer": "yes"})

langfuse.flush()
print("Sent.")