# Decisions

Filled in as each decision is made, not retroactively. Empty sections below
are placeholders for phases not yet built.

## Phase 1 — Skeleton

**Decision:** Config is env-var driven from the start (`app/config.py`),
including the LM Studio base URL, even though only one env var matters right
now. Reason: every later phase (model routing, Pinecone vs pgvector, cloud
model comparison) is a config swap instead of a code change if this is right
from day one.

**Decision:** `docker-compose.yml` includes commented-out service blocks for
Postgres/pgvector and Langfuse rather than adding them fresh in later phases.
Reason: the shape of the eventual stack is visible from Phase 1, and
uncommenting is a smaller diff than writing new service blocks later —
easier to point to in an interview as "I designed the compose file knowing
where this was going."

---

## Open questions to answer as later phases land

1. Why the approval gate sits where it does, and what it costs in latency
2. Why order lookup is structured and policy answers are RAG
3. Which chunking strategy won, measured how
4. Whether hybrid search and reranking actually improved recall, with numbers
5. pgvector vs Pinecone: what was measured and which ships
6. When to reach for prompting, RAG, or fine-tuning — this project as the
   worked example of all three on the same task
7. What happened when the two policy documents contradicted each other
8. ReAct vs plan-and-execute: which one ships and why
9. What LangGraph took over that was previously done by hand
10. Why tools are exposed over MCP rather than called directly
11. Why self-hosted inference here, and when to switch to an API model
12. How regressions are caught when a prompt changes
13. What traces make debuggable that logs alone would not
14. Whether fine-tuning was worth it, with numbers
