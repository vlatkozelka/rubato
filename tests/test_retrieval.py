import asyncio

from services.retrieval_service import retrieve_chunks

print("PASS NUMBER 1")
results = asyncio.run(retrieve_chunks("How many days do I have to return an opened software license?"))
for r in results:
    print(f"[{r.source} / {r.chunk_index}] {r.text}")


print("PASS NUMBER 2")
results = asyncio.run(retrieve_chunks("How many days do I have to return an opened software license?"))
for r in results:
    print(f"[{r.source} / {r.chunk_index}] {r.text}")