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


## Phase 2 — Composite vs. complex_case

**Decision:** Split what was originally one vague "complex_case" escape
hatch into two distinct intents: `composite` (multiple KNOWN, independent
asks in one message) and `complex_case` (the resolution path is genuinely
unknowable without looking up facts first).

**Why:** initial testing showed a message like "where's my order, and
what's your return policy?" landing on a single intent lost information —
there was no way for the router to know two separate, answerable questions
were both present. But conflating that with the canonical complex case
(broken zipper + prior return + "what can you do?") would have been wrong
in the other direction: that case has no fixed list of sub-intents to
report, since the correct resolution only emerges after checking order
history, return history, and stock. Forcing both into one bucket would
have made `composite` meaningless (sometimes populated, sometimes not) and
kept `complex_case` doing double duty as both "genuinely unknown" and
"here's a known list, just go run it."

**Conflict handling:** composite is only valid when sub-intents are
independent. Introduced `ConflictingIntentPair` as an explicit, structured
list (currently: refund_request + return_request — mutually exclusive
resolutions for the same item) rather than describing conflicts only in
prose. The system prompt is generated from this list at runtime, so
conflict rules live in one place and can be reused by the eval suite later
instead of only existing as unstructured prompt text.

**Relevance to later phases:** this distinction gives a concrete, tested
answer to interview question #8 (ReAct vs. plan-and-execute). `composite`
requests are a natural fit for plan-and-execute — the full set of steps is
already known up front (do X, do Y, merge). `complex_case` requests are the
actual argument for ReAct, since the next step can't be planned until the
previous one's result is known.

**Also added:** a `chitchat` intent, after testing showed a bare "hey"
being forced into `complex_case` — the enum had no correct answer for a
message with zero support-related content, so the model picked the least
appropriate option available. `chitchat` gets a generic redirect response,
handled without invoking the agent loop.


## Phase 2 — Composite/conflict design, kept as an experiment

**Decision:** Built the advanced triage schema (composite intent + explicit
conflict pairs) now, in Phase 2, rather than deferring it to Phase 13
(model routing/optimization) as originally recommended.

**Context:** the case against building this now was real — it's a routing
optimization, not a correctness fix (unlike `chitchat`, which fixed an
actual bug). Skipping it entirely and routing every multi-part or
ambiguous message to `complex_case` would not have broken anything; the
agent loop in Phase 9 can resolve those messages correctly on its own,
just less efficiently. The risk of adding this later, as a pure addition
to the schema, was assessed as low.

**Why built anyway:** the working hypothesis is that real customer
messages are messy and often genuinely multi-part often enough that
letting all of it fall through to `complex_case` would waste a
disproportionate number of requests on the expensive agent-loop path —
not because the phrasing is unclear, but because customers frequently
ask more than one thing per message. This is a genuine hypothesis, not
a settled fact — the counter-argument (most traffic is single-intent
once noise is stripped, and this is premature optimization on a
hand-picked adversarial test set) is equally plausible and was not
disproven, just deprioritized in favor of testing the hypothesis
directly with a real design instead of arguing it further in the
abstract.

**This is being tracked as an experiment, not a proven best practice.**
The real test comes in Phase 12 (evals): if the golden dataset shows
composite/conflict cases are rare in realistic traffic, or that the
extra schema complexity doesn't measurably reduce agent-loop
invocations, this should be simplified back toward the binary
complex/not-complex design — the added surface area (an extra intent,
a nullable list field, a conflict-pair schema, extra few-shot examples)
isn't worth carrying if it's not earning its keep. Revisit this
decision once real accuracy/latency/cost numbers exist, not before.

---

## Enums for Intent and NodeId, and a LangGraph limitation

Replaced raw strings for `Intent` and node names with `(str, Enum)`
classes, to get validation-at-parse-time instead of silent typos
(e.g. `"order_stauts"` passing through unnoticed).

Known LangGraph limitation: passing Enum members directly to
`add_node`, `set_entry_point`, and `add_conditional_edges` broke
graph execution silently — no error, but the entry node never ran.
This is a documented issue (langgraph #2964: "Cannot use Enums for
node names"), not a design mistake on our end.

Fix: `NodeId` and `Intent` stay as enums everywhere in our own code
for readability and validation, but every call into LangGraph's API
(add_node, set_entry_point, add_conditional_edges source/path_map)
uses `.value` to pass a plain string. Worth remembering if we ever
add a new node: the `.value` requirement applies there too.

Also, `traverse()` currently has no `case _:` fallback — an intent
that falls through without a matching case silently returns `None`.
Python's `match` doesn't enforce exhaustiveness the way Kotlin's
`when` does over a sealed class. Flagged, not yet fixed.

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
