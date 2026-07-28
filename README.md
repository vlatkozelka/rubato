# Rubato

An AI customer support copilot for a fictional e-commerce store — built to
exercise, end to end, the concepts that show up on real AI engineer job
descriptions: structured output, tool calling, MCP, RAG (with hybrid search
and reranking), agent loops (ReAct and plan-and-execute), memory, guardrails,
evals, tracing, and a small LoRA fine-tune, all measured rather than assumed.

Full build plan and rationale: see `PLAN.md`. Decisions made along the way,
and why: see `DECISIONS.md`. Eval results: see `EVALS.md` (from Phase 12 on).

**Status: Phase 1 — skeleton.** One endpoint, hardcoded response. Real triage
and routing start in Phase 2.

## Quick start

Requires [LM Studio](https://lmstudio.ai) running locally with a model loaded
and the local server started (default port 1234).

```bash
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/support/message \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "c1", "customer_id": "cust_002", "message": "Where is my order?"}'
```

### Running without Docker

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Project layout

```
app/            FastAPI app, config, (later) graph/agent code
data/           Sandbox store data: products, orders, customers, return history
docs/           Store policy docs used for RAG (includes a deliberate
                contradiction between return-policy.md and warranty.md)
tests/          Eval suite and unit tests (from Phase 12)
```

## Why this domain

Customer support for e-commerce is boring on purpose — instantly legible to
any interviewer, and it naturally requires structured lookups, grounded
retrieval, tool use, multi-step reasoning, and a real human-approval gate
without any contrivance. The domain isn't the point; the architecture is.
