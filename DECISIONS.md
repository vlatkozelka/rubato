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


## Phase 2 — Triage

**Decision:** Use `instructor.Mode.JSON_SCHEMA` for structured triage output,
not the library default (`Mode.TOOLS`) or `Mode.JSON`.

**What happened:** `Mode.TOOLS` failed — LM Studio's server only supports the
OpenAI spec's string-enum form of `tool_choice` ("auto"/"required"/"none"),
not the object form that names a specific function, which is what instructor
sends by default. `Mode.JSON` failed too — LM Studio's server only accepts
`response_format.type` of `"json_schema"` or `"text"`, rejecting the looser
`"json_object"` shape outright.

`Mode.JSON_SCHEMA` and `Mode.MD_JSON` both worked, but not for the same
reason. `JSON_SCHEMA` sends the actual schema to the server, which compiles
it into a grammar and constrains token generation — the model structurally
cannot emit invalid output. `MD_JSON` just prompts the model to wrap JSON in
a code fence and parses it client-side with no server-side enforcement; it
happened to work because the local model is instruction-following enough for
a simple schema, not because anything guarantees it will.

**Why this matters:** self-hosted inference servers (LM Studio/llama.cpp)
implement a subset of the full OpenAI API surface, and that subset boundary
is invisible until you hit it. A hosted API (OpenAI, Anthropic) would have
accepted the default `Mode.TOOLS` call without complaint. This is a concrete
answer to "why self-hosted here, and when would you switch to an API model"
(interview question #11): local serving is free and private, but you inherit
whatever gaps exist in that server's API compatibility, and you have to know
enough to diagnose that rather than assume any OpenAI-shaped client "just
works" against it.

**Chosen:** `Mode.JSON_SCHEMA` as the primary mode going forward, since it's
enforced at generation time rather than hoped-for. `Mode.MD_JSON` is worth
keeping in mind as the universal fallback for any future backend that
doesn't support schema-constrained decoding at all.

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
