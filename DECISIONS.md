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


## Phase 6 - Approval Gate: Hand-Rolled Queue vs LangGraph `interrupt()`

**Decision:** Refund approval is a decoupled queue (Option B), not a paused
graph execution (Option A).

**Why:** LangGraph's `interrupt()` pauses a single execution for a human to
resume *that same run* — a good fit for something like a supervised coding
agent where a human is actively watching. A refund approval queue is reviewed
asynchronously, in arbitrary order, by any staff member, possibly days later.
That's not one paused execution, it's two decoupled systems (agent decision,
human execution) connected by a database record.

**Implementation:** The `refund_request` node computes eligibility/amount,
writes a `pending` row to the `approvals` table with the reasoning, and the
graph run ends normally. `POST /approvals/{id}/approve` is a separate code
path that executes the refund directly — it does not resume the graph.

**Revisit when:** Phase 8 adds a persistence layer. Worth reassessing then
whether `interrupt()` + a checkpointer is a better fit for the complex-case
agent loop (Phase 9), which is closer to the "active supervision" case than
refunds are.

## Infra detour — Postgres migration + JWT auth (2026-08-01)

Done as an out-of-band detour between Phase 5 sessions, not as a numbered
phase. Sandbox JSON files (`data/*.json`) are gone; `products`, `customers`,
`orders`/`order_items`, `return_history`, and `users` now live in Postgres,
seeded entirely from SQL in `db/init/`. See `PLAN.md` for the note on where
this sits relative to phase numbering.

**Order status schema:** kept the flat `status_kind` column + a single
nullable `delivered_at` column on `orders`, rather than a separate
status/events table. This mirrors the shape orders.json already had, and
`Order`'s `model_validator(mode="before")` (models/order.py) already knows how
to reassemble the four-way discriminated union from exactly that shape, so
`order_service.py` builds the same flat dict and hands it to `Order(**raw)`
unchanged. Only `delivered` currently carries extra data (`delivered_at`); if
a future status needs its own fields, a JSONB column or a real status-history
table is the better move — one nullable column per status doesn't scale past
one or two.

**Order items:** snapshot `name` and `price` on `order_items` instead of only
storing `product_id` and joining to `products` for display. This matches what
`orders.json` already did (repeating name/price per line item) — intentional,
since a historical order should keep showing what the customer actually paid,
even if the product is later renamed or repriced.

**Users table — SUPERSEDED, see "Customers own their own auth" below.**
~~One `users` table with a `role` CHECK ('staff'/'customer') and a nullable
`customer_id` FK, instead of a separate `staff_users` table. Staff and
customer accounts authenticate identically (email + password_hash, one
`/auth/login` endpoint, one JWT shape); the only structural difference is
whether a customer link exists, which one nullable column and a
`CHECK ((role = 'customer') = (customer_id IS NOT NULL))` constraint express
without a second parallel schema. Same reasoning as the `status_kind` +
nullable-column choice above — a discriminator column over a second table
when the two cases share almost everything.~~ Reconsidered almost
immediately: the customer↔user relationship this modeled is strictly 1:1
(every seeded customer has exactly one login, never zero or several), so
the "discriminator column over a second table" argument didn't actually
apply — there was no real 1:many relationship being simplified, just an
extra table plus a duplicated `email` column (`customers.email` and
`users.email`, nothing keeping them in sync). Kept here, not deleted, per
this file's own convention for superseded entries.

**JWT, no refresh token:** access tokens only, 60-minute expiry
(`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`), no refresh token or rotation. This is a
portfolio sandbox exercised by short manual/API sessions, not a product with
real user sessions to keep alive — a refresh flow adds real surface
(rotation, revocation, storage) for no exercised benefit yet. Revisit if this
project ever grows a UI where a human sits in a session longer than an hour.

**customer_id: token, not body.** `POST /support/message` used to take
`customer_id` in the request body; it's now dropped from
`SupportMessageRequest` entirely and derived from the JWT (`principal.customer_id`
via `require_customer`). Chose "derive from token" over "check token matches
body" because it removes an entire class of bug (trusting a client-supplied
identity field) rather than just detecting it — the token is already the
source of truth for who's asking, so asking the client to also state it and
then verifying agreement is redundant. This is a breaking change to the
request shape, acceptable since there are no external consumers of this API
yet.

**Full-text product search (supersedes the word-overlap note in the old
`product_service.py`):** `get_products_by_name` no longer does naive
word-overlap matching over an in-memory list — see the "Naive word-overlap
matching..." comment that used to sit in that file, which explicitly named
Postgres full-text search as the fix once the data left JSON. That's what
this is. `products.search_vector` is a `GENERATED ALWAYS AS ... STORED`
`tsvector` (name weighted 'A', category weighted 'B'), indexed with GIN, and
queried with `websearch_to_tsquery` + `ts_rank_cd` — `websearch_to_tsquery`
because it's the one built to parse how people actually type free-text
queries (quotes, `-exclude`, implicit AND), which is closer to a customer
support message than `plainto_tsquery`. Chose a generated column over a
trigger because `to_tsvector('english', text)` is immutable when the config
name is a literal, so Postgres can maintain it automatically with no
trigger function to keep in sync — the tradeoff is the generated expression
lives in the `CREATE TABLE` statement rather than being swappable at
runtime, which is fine here since there's one search config, not several.

Also added a `pg_trgm` trigram index on `name` as a fallback path,
specifically for typos (e.g. "sweter" → "Sweater") — a realistic scenario
in support chat that full-text search alone doesn't catch, since
`to_tsvector` matches word stems, not near-misses. Used `word_similarity()`
with a manual `> 0.3` threshold rather than the `<%` operator (whose default
threshold is 0.6, tuned for longer text) — a short query like "sweter"
against a multi-word product name scored 0.5 in testing, correctly above a
0.3 bar but below 0.6. At catalog sizes beyond a 20-item sandbox, switch to
`<%` with `SET pg_trgm.word_similarity_threshold` so the trigram GIN index
gets used instead of a sequential scan; not worth the added config at this
scale. This full-text/trigram work is unrelated to the hybrid-search work
PLAN.md already scopes for Phase 4b (`policy_chunks`, RAG) — same Postgres
features, different table, different purpose (product lookup vs. grounded
policy answers).

**Approval endpoints didn't exist yet — added minimal versions to have
something to gate.** `GET /approvals`, `POST /approvals/{id}/approve`, and
`POST /approvals/{id}/deny` were fully specified in PLAN.md (Phase 6) and the
`approvals` table + `Approval` model already existed, but no route or service
implemented them before this detour. Added `services/approval_service.py`
(list pending, flip status) and the three routes, gated to `require_staff`.
Deliberately did **not** implement refund execution (charging back an order,
updating stock, etc.) — that's real Phase 6 business logic and out of scope
here. `POST /approvals/{id}/approve` currently only flips `status` to
`approved`; wiring an actual money-moving action into that path is Phase 6
work.

**Not pooling DB connections.** `order_service.py`, `customer_service.py`,
`product_service.py`, `customer_auth_service.py`, `staff_auth_service.py`,
and `approval_service.py` all open a new `psycopg.connect()` per call, same
as the pre-existing
`retrieval_service.py`/`index_docs.py` pattern. Consistent with what was
already there, not a new decision, but flagging it as a known follow-up:
worth moving to a shared connection pool (`psycopg_pool`) once request volume
in evals/load-testing makes per-call connection overhead visible.

**Password hashing:** `bcrypt` directly, not `passlib`. `passlib`'s bcrypt
backend has had compatibility breakage against bcrypt >=4.x releases
(version-introspection code that assumes an older internal API), and the
direct `bcrypt.hashpw`/`bcrypt.checkpw` calls in `app/security.py` are a
three-line wrapper — not enough surface for an abstraction layer to earn its
keep. Seed passwords are generated via pgcrypto's `crypt(password,
gen_salt('bf', 10))` directly in `db/init/006_seed_customers.sql` and
`db/init/012_seed_staff_users.sql`, which produces standard `$2a$` bcrypt
hashes that `bcrypt.checkpw` reads without any Python-side seeding step —
verified compatible in testing.

**No self-serve registration.** Seed data only: one staff account
(`staff@rubato.test`, `db/init/012_seed_staff_users.sql`) and one customer
account per seeded customer (`db/init/006_seed_customers.sql`), each side
sharing its own fixed demo password documented in `README.md`. This is a
portfolio sandbox with a fixed cast of customers; a registration endpoint
would be unused surface with no real signup flow behind it (no email
verification, no self-serve UI) — explicitly out of scope per the task this
detour was scoped from.

**Customers own their own auth; staff get a separate, minimal table.**
Reworked the "Users table" decision above after a review question: does
splitting *login* into two services (a customer login and a staff login,
each reflecting a distinct future UI) complicate every call site that
requires auth? It doesn't, because `password_hash` now lives directly on
`customers` (removing the duplicated-email problem the old `users` table
had) and staff get their own `staff_users` table with no FK back to
`customers` and no `role` column at all — membership in that table already
means "staff". `services/customer_auth_service.py` and
`services/staff_auth_service.py` are the two login-side services the user
asked for, each returning its own domain model (`Customer` / `StaffUser`).

What stayed the same, and why this didn't ripple into every auth-gated
route: verification and authorization were already decoupled from *which*
login issued the token. `app/auth.py`'s `get_current_principal` /
`require_staff` / `require_customer` dependencies only ever produce and
check `models/auth_principal.py`'s `AuthPrincipal` (`sub`, `role: UserRole`,
`customer_id`) — never a `Customer` or `StaffUser` object directly. So
splitting the login services only touched the two `/auth/*/login` routes
and `app/security.py`'s `create_access_token`, which now takes
`(subject_id: str, role: UserRole)` instead of a table-backed `User` model.
`app/auth.py` needed zero changes. This is also why the JWT no longer
carries a separate `customer_id` claim: a customer's own `id` (e.g.
`cust_001`) is already their login row's id, so `sub` doubles as
`customer_id` when `role == customer` — `decode_access_token` sets
`customer_id = sub` for that role and `None` for staff.

## Customer login + chatbot UI, and API response formatting (2026-08-01)

Done as an out-of-band task between phases, same pattern as the Postgres/JWT
infra detour above — not a numbered phase, but real functionality landing on
top of the auth work that detour left in place.

**UI stack: static HTML + vanilla JS, served by FastAPI, no build step.**
Two pages (`static/login.html`, `static/chat.html`), one shared stylesheet,
one JS file per page, served via `StaticFiles` mounted at `/assets` plus two
explicit `FileResponse` routes (`GET /login`, `GET /chat`) in `app/main.py`.
No Jinja2, no bundler, no frontend framework.

**Why no build step:** the entire UI is two forms and a message list — no
client-side routing, no shared component state beyond "list of chat
messages," nothing a framework's diffing/state-management would meaningfully
simplify. A build step (npm, bundler config, JSX transform) is a second
toolchain next to the Python one, for a two-page portfolio demo whose entire
value is "an interviewer can read the whole thing in five minutes." Same
"boring over clever" bias as the rest of this project. Revisit only if this
UI ever grows real client-side state (e.g. multi-conversation history,
optimistic updates) that a plain `fetch` + DOM-append loop can't express
cleanly.

**Why not server-rendered (Jinja2) either:** neither page needs server-side
data at render time — the login form is static, and the chat page's only
"data" (the token, the message list) lives entirely client-side after
login. Jinja2 would add a templating dependency to solve a problem
(injecting server data into HTML) that doesn't exist here. If a future page
needs server-rendered data (e.g. a staff approval queue listing pending
approvals), Jinja2 becomes the right call there — noted for that not-yet-
built page, not retrofitted onto these two.

**Token storage: `sessionStorage`, not `localStorage` or an httpOnly
cookie.** Chose the middle option deliberately:
- Plain in-memory JS variable is the most XSS-resistant (no persisted copy
  for a malicious script to read after the fact) but is lost on any page
  refresh — for a chat UI where a refresh is a normal thing to do
  mid-conversation, that's a real usability cost for a marginal security
  gain in a two-page demo with no third-party JS on the page (no npm
  supply chain = the realistic XSS surface here is near zero).
- `localStorage` persists indefinitely across browser restarts, which is
  more exposure window than this needs — a stolen token from an old,
  forgotten tab is a worse outcome than one that dies when the tab closes.
- `sessionStorage` clears when the tab closes but survives a same-tab
  refresh, which matches how this demo is actually used (one login, one
  chat session, closed when done) without the indefinite-persistence
  downside of `localStorage`.
- An httpOnly cookie is the strongest option against XSS (JS can't read it
  at all) but this API is a stateless Bearer-token API (`Authorization`
  header, no server-side session), not cookie-based — switching to cookies
  means also building CSRF protection (SameSite alone isn't sufficient
  once a form/fetch can be triggered cross-site), which is real backend
  surface to add just to store the token more safely. Disproportionate for
  a two-page demo; this is the concrete next step if this ever became a
  real product with a real session lifetime (see the "no refresh token"
  decision above — same "not yet, but here's the upgrade path" shape).

**No client-side conversation history persistence.** `conversation_id` is a
fresh `crypto.randomUUID()` generated on page load, held only in a JS
variable — matches the task's "message history for the session" framing.
Reloading the chat page starts a new conversation; nothing is lost that
matters for a demo, and building persistence (localStorage transcript,
or a server-side conversation store) is real scope `ConversationState`
doesn't support today anyway (each `/support/message` call constructs a
fresh `ConversationState`, not one loaded from a prior turn — multi-turn
memory isn't wired up yet, so the UI shouldn't imply it is).

**No markdown rendering.** `greet_node`'s reply contains a markdown-style
bullet list (`- Check the status...`). Rendered as plain preformatted text
(`white-space: pre-wrap` in CSS) rather than parsed as markdown — pulling in
a markdown-to-HTML library for one node's bullet list isn't worth a new
dependency. Line breaks and indentation still show correctly; only the
`-` stays literal instead of becoming a `<li>`. Revisit if reply content
starts using markdown more heavily (e.g. bold/links in RAG answers).

**No staff UI, by design.** Explicitly out of scope for this task — no
`/auth/staff` page, no approval-queue page. The staff login endpoint and
`/approvals/*` endpoints are untouched and still API-only.

### API response formatting

**The bug:** `POST /support/message` had a `response_model=SupportMessageResponse`
declared, but the handler built `reply=f"{result}"` where `result` was the
raw dict LangGraph's `.invoke()` returns (a serialized `ConversationState`)
— so the "clean" response model was wrapping a Python repr dump of the
entire conversation state (including nested `Order`, `TriageResult`, enum
reprs like `<Intent.ORDER_STATUS: 'order_status'>`) inside one string field.
Declaring a `response_model` doesn't help if a handler stuffs an object
dump into a field FastAPI can't see is wrong, because the field is typed
`str` and any string validates. `check_price_node` had the same class of
bug one level down — `f"...{products}"` interpolated a `List[Product]`
directly into the result string, and `composite_node` interpolated a raw
`Intent` enum member the same way (`f"...{first_sub_intent}..."`, which
prints as `Intent.ORDER_STATUS`, not `order_status`) — see the "Enums for
Intent and NodeId" decision above for why `(str, Enum)` doesn't
`str()`/`f-string`-format the way it might look like it should.

**Fix:** `app_graph.invoke(state)` result is now revalidated back into a
`ConversationState` (`ConversationState.model_validate(raw_result)`)
instead of interpolated directly, and `app/main.py` builds the response
from its typed `results: List[IntentResult]`, not from the raw graph
output. `check_price_node` gained a `format_price_matches()` helper
(same pattern as the pre-existing `format_order_status()` right next to
it) instead of interpolating `Product` objects into a string.
`composite_node` now uses `.value` on the sub-intent, same fix
`traverse()` already needed for the same reason. All three are string-
formatting fixes at the point results get turned into user-facing text —
not changes to triage/routing/RAG logic itself.

**Response shape decision — what "clean" means for a chat reply.** The
task brief referenced an `outcomes: Dict[str, str]` shape on
`ConversationState` as the thing to design around; the actual field is
`results: List[IntentResult]` (`intent: Intent`, `result: Optional[str]`,
now also `citations: Optional[List[str]]`) — noting the mismatch here
since the brief may have been written against an earlier/hypothetical
version of this model. Designed the response mapping against what's
actually in the codebase:
- `SupportMessageResponse.reply: str` — every non-empty `IntentResult.result`
  in `results`, joined with blank lines. For the common case (one intent,
  one result) this is unchanged from before. For `composite` messages,
  `results` holds more than one entry (`composite_node`'s own "I'll handle
  X first" plus the resolved sub-intent's result), and joining both is more
  informative than showing only one — previously this case wasn't visibly
  distinct anyway since the whole response was broken.
- `SupportMessageResponse.intent: Optional[Intent]` — the *last* result's
  intent, i.e. the actually-resolved outcome (for `composite`, that's the
  resolved sub-intent, not the literal `composite` tag) — chosen because
  this is what a UI would want to branch on to decide how to render the
  reply (e.g. "show a citations block").
- `SupportMessageResponse.citations: Optional[List[str]]` — sourced from
  `IntentResult.citations`, a new field populated only by
  `answer_policy_question_node` from `PolicyAnswer.cited_sources` (which
  existed already but was being silently dropped — only `.answer` made it
  into `IntentResult` before). Kept as a flat list of source strings
  (`"return-policy.md#Opened software"`) rather than inventing a richer
  citation object, since that's the exact shape `PolicyAnswer` already
  produces and there's no UI need yet for more structure than "list these
  under the reply."
- Deliberately **not** exposed: `PolicyAnswer.grounded`, or any
  intent-specific structured payload (e.g. a separate `order` object
  mirroring `models/order.py` for an order-status "status card"). Order
  status and price-check replies are already fully rendered into `reply`
  as clean text by their respective `format_*` helpers — a parallel
  structured field would duplicate that text as data with no current
  consumer. If a future UI wants a richer order-status card (e.g.
  clickable line items), that's the point to add an intent-specific
  optional field, not before.

**Existing endpoints (`/auth/*/login`, `/approvals*`) were already
correct** — each already declares an explicit `response_model` and maps a
Postgres row to a real Pydantic model (`Approval`, `LoginResponse`) before
returning, no service/domain object leaking through. `/support/message`
was the only endpoint actually returning an unserialized object dump; no
changes were needed elsewhere for "ideally all endpoints."


## Refund Eligibility: RAG-Backed Policy Window, Not Hardcoded

**Decision:** `refund_service.check_refund` retrieves the applicable refund
window (`allowed_duration`) via RAG (`get_refund_policy`, a structured
`instructor` call over retrieved policy chunks) rather than hardcoding
per-category day counts in code.

**Why:** The window itself lives in `return-policy.md` / `warranty.md` and is
legal/business-owned, editable content — not application logic. Hardcoding it
would mean every policy change (legal updates the electronics window from 14
to 21 days) requires a code change and redeploy. With RAG, the same change is
a document edit + re-embed; `refund_service` picks it up on the next call with
zero code touched.

**Split preserved:** The window *lookup* is non-deterministic (LLM +
retrieval, appropriate since the source is unstructured prose). The
eligibility *decision* (`days_since_delivery <= allowed_duration`) stays
deterministic, in code, since it's pure arithmetic with no ambiguity to
resolve. RAG is used only where determinism isn't achievable for free;
everything else stays deterministic, especially since this sits on the
money-moving path.

**Verified:** order `ord_1001`, category `electronics`, delivered 27 days ago,
policy correctly retrieved a 14-day window, correctly denied. Confirms the
window is genuinely coming from the document, not a coincidental hardcoded
match.

## Phase 7 — MCP

**Why MCP at all.** Tools were already plain service functions callable by direct import — MCP adds no functional capability today, only a transport boundary. The cost (latency per call, added process, added complexity) is paid now for a real payoff later: Phase 9's agent loop needs tools addressable by name/schema independent of Python import paths, and MCP tools are trivially reusable by other clients/machines (a different LLM backend, a future service) without code changes. Net: a deliberate cost taken early for reuse and decoupling, not a functional requirement of Phase 7 itself.

**HTTP over stdio.** stdio ties the tool server to the same machine/process tree as its caller. HTTP keeps the MCP server genuinely swappable to another machine with just a URL change — matches the standing rationale that tools should be reachable from other processes later (a different LLM backend, a separate agent host), not just this one local graph.

**Auth: static shared key, not JWT.** Originally planned as JWT (signature, expiry, claims). Reconsidered once the actual trust boundary was clear: this is two processes on one machine, owned by the same system, never crossing a real network trust boundary — JWT's machinery (expiry handling, signature verification, claims) solves a multi-party/multi-machine identity problem that doesn't exist here. Landed on a static shared key compared with `secrets.compare_digest` (constant-time, avoids timing-attack leakage) instead of `==`. Upgrade path if this ever needs real multi-client or cross-machine identity: JWT or full OAuth.

**Separate auth layer from the app's existing JWT.** `app/auth.py` authenticates end users (customers/staff) through the public API surface. `mcp_server/auth.py` authenticates the graph process to the MCP process — a different trust boundary entirely, so no code reuse was forced between them.

**`session.call_tool()` over `get_tools()`/agent-style `Tool` wrapping.** `langchain-mcp-adapters` offers two calling patterns: `get_tools()` converts MCP tools into LangChain `Tool` objects for an LLM to choose between (the agent pattern — Phase 9's use case), versus `client.session(...)` + `session.call_tool(name, args)`, calling a named tool directly with known arguments. Phase 7's nodes already know exactly which tool they need — routing decided that upstream in triage — so there's no tool-selection happening here. Using `get_tools()` would add agent-oriented machinery for a call site that isn't an agent. `session.call_tool()` matches the phase's actual intent: same control flow, just crossing a protocol boundary.

**Stateless client, no persistent session.** Considered hand-rolling a persistent MCP session with reconnect-on-failure logic (background thread, dedicated event loop) to avoid paying connection setup cost per call. Dropped in favor of `MultiServerMCPClient`'s default stateless behavior — a fresh session per call — because the MCP server holds no cross-call state, so there's nothing a persistent session buys here beyond avoided setup latency, and "reconnect after a drop" isn't a problem when every call already opens fresh. Revisit only if per-call connection overhead is measured as an actual bottleneck (Phase 13 territory, not assumed now).

**`structuredContent["result"]` unwrapping for list-returning tools.** FastMCP wraps non-object return types (e.g. `list[Product]`) under a `"result"` key in `structuredContent` — confirmed by direct inspection, not documented obviously. Every tool converted from a list-returning service function needs this unwrapping; noted here so it's not independently rediscovered (or inconsistently guessed at) per tool, including by whatever hands off the remaining tool conversions.

**Async boundary: converted only what MCP calls touch.** `check_price_node` and its MCP-calling path went `async def`; nodes with no MCP/network dependency (e.g. `triage_node`) stayed sync deliberately — converting them would be a real, separate piece of work (a genuine async migration across LLM-calling nodes) mistakenly folded into a transport-boundary phase. Logged as a candidate for Phase 13, not done here.

---


## Phase 8 — Conversation history format for triage

History is passed to the LLM as structured multi-turn messages (prior
`Turn`s appended into the `messages` list before the current message),
not flattened into a single string. This uses the chat endpoint's native
multi-turn format directly, so `instructor` needs no custom parsing.

The system prompt was extended to explicitly tell the model that a short
reply (an order ID, a bare "yes") may be answering a question the
assistant itself just asked, and to classify the current message in that
light. Without this, "ord_1011" alone triage'd as order_status; with
history + the instruction, it correctly resolved as a refund_request
continuation, including running eligibility and correctly denying it on
the return window.


## Phase 8 — Token-budget summarization

History above HISTORY_TOKEN_BUDGET (3000, ~12K chars) gets compacted:
last 6 turns kept verbatim, everything older collapsed into one
LLM-generated summary turn. Token estimate is a char/4 heuristic — no
local tokenizer available via LM Studio's API, so this is approximate.

Summary turn uses role="assistant" (prefixed "[Earlier conversation
summary]: ..."), not role="system" — most chat-completion APIs only
support system as the leading message. Using assistant keeps the
sequence in the alternation triage already expects.

Budget is 3000 despite the local model's 256K context window —
deliberate, not a hardware constraint. Lost-in-the-middle degradation
and per-request latency/cost don't go away just because the window is
big; the budget reflects what triage needs to classify correctly, not
what the model can technically hold.

Compaction runs in save_conversation_turn, after appending new turns
and before the write, so Postgres always holds the current-best
representation rather than re-summarizing on every load.

---

## Phase 8 — customer_profiles: long-term memory, minimal and write-path complete

Added customer_profiles (customer_id PK, refund_request_count,
last_contacted_at, notes) as a deliberate portfolio artifact for the
"long-term memory, structured, not RAG" concept — not blocking any
functional need. Phase 9's return-history abuse check is better served
as a plain on-demand lookup, same pattern as order_service, not folded
into this table.

Kept to columns with non-redundant justification vs. existing data
(customers table, orders, return_history.json). Seeded non-uniformly
across cust_001-006 for realistic test fixtures.

Initially shipped as read-only (seeded, no setters) — caught as a real
gap, not "memory" if nothing writes to it. Added update_last_contacted
(every request) and increment_refund_request_count, fired only on
genuine refund decision outcomes (approved or denied), not on
incomplete requests or pre-decision rejections.

notes deliberately has no setter yet. Considered an LLM-generated note
past a request-count threshold, but whether it should be stored at all
vs. computed on-demand at the point of actual use has no answer without
a real consumer — deferred to whichever phase first reads it.


## Phase 7 (gap) — return_history had no service layer or MCP tool

**What was missed.** `return_history` (schema + seed data, added in the
Postgres migration detour) was never given a service module or an MCP tool
during Phase 7's tool conversion — every other read-only domain object
(orders, products, stock, refund eligibility, policy docs) was converted,
this one wasn't. Not caught until Phase 9 needed it for the return-history
abuse check called out in the Phase 8 customer_profiles entry above.

**Fix, added now as a Phase 9 prerequisite, not part of Phase 9 itself:**
`services/return_history_service.py` (`get_return_history(customer_id)`,
same per-call-connect `psycopg.AsyncConnection` pattern as `order_service`/
`product_service`, most-recent-first) and `mcp_server/tools/return_history.py`
(`get_return_history_tool`, registered in `mcp_server/__init__.py` same as
every other tool module). List-returning, so it needs the same
`structuredContent["result"]` unwrapping documented in the Phase 7 MCP
section above — verified directly (not assumed) against the real server:
without the unwrap, `structuredContent` came back `None` and the rows were
only reachable by parsing each `content[i].text` as JSON.

**Read-only, deliberately.** Only a lookup method was added — no insert/
write path — since none was scoped for this task. `initiate_return`
(`services/return_service.py`) already covers starting a new return; whether
that should also append to `return_history` is a separate decision, not
addressed here.

**Not wired into any graph node.** This only makes the tool callable
(verified with a direct MCP client call against seeded data, customer
`cust_006` → 2 rows, most recent first). Wiring it into the `complex_case`
loop is Phase 9's actual next step.

**Verified:** `mcp_client.call_tool("get_return_history_tool", {"customer_id":
"cust_006"})` against the seeded DB returned both `cust_006` rows
(`ord_1018`, `ord_1012`), most-recent-first; a customer with no returns
(`cust_001`) correctly returned `[]`.

## Phase 9 (prep) — Dropped `composite`, collapsed `results` into `reply`

**Decision:** Removed the `composite` intent, `sub_intents`, `composite_node`,
and the `ConflictingIntentPair`/conflict-pair machinery entirely. Collapsed
`ConversationState.results: List[IntentResult]` into a single
`reply: Optional[str]` + `citations: Optional[List[str]]`. This is a
deliberate reversal of the Phase 2 experiment (see "Composite vs.
complex_case" and "Composite/conflict design, kept as an experiment" above),
not an oversight — that entry already flagged this as revisitable once real
usage data existed; what actually triggered the reversal is different from
what that entry anticipated (see below).

**Why composite was dropped.** It existed to let triage chain independent
simple intents deterministically (`sub_intents`, run each in turn). The
Phase 9 agent loop makes this redundant: an agent that can plan and call
tools freely handles a multi-intent message natively, without a separate
mechanism for detecting and chaining independent sub-intents. With
`composite` gone, `complex_case` now covers both cases it always partially
owned — genuinely unknowable resolutions AND multi-intent messages,
independent or conflicting alike — since every multi-intent message now
needs the same thing: a node that can reason over more than one ask, which
is exactly the agent loop.

**Why `results` became `reply`.** With `composite` gone, every request runs
exactly one terminal node. `results: List[IntentResult]` existed to
accumulate output across chained sub-intent nodes; with nothing left to
chain, it always held exactly zero or one entries. Collapsed to a single
`reply` + `citations`, read directly off `ConversationState` instead of
filtered/joined from a list. The intent is already available on
`triage_result`, so `IntentResult`'s intent→result mapping had nothing left
to provide either — deleted.

**Why the conflicting-intent-pair machinery went with it.** It only ever
performed conflict *detection* for routing purposes — telling triage "these
two intents together mean `complex_case`, not `composite`." It never
performed conflict *resolution*. With `composite` gone, every multi-intent
message routes to `complex_case` regardless of whether the intents conflict,
so the detection distinction has nothing left to disambiguate.

**The conflict rule itself, recorded here so it isn't lost with the class:**
refund (money back) and return-for-exchange are mutually exclusive remedies
for the same item — the customer must end up with one outcome, not both.
This moves into the complex-case agent's system prompt when that node is
built (Phase 9 proper). Resolution policy: when two requested outcomes are
mutually exclusive and no retrieved fact settles which applies, the agent
must NOT choose — it states the options and asks the customer which they'd
prefer. Rationale: refund vs. exchange is a customer preference, not a
discoverable fact; no tool call can resolve it, guessing "first stated"
treats word order as intent priority, and guessing "cheaper remedy" resolves
ambiguity in the business's favor against a stated preference. Phase 8's
history-aware triage makes the follow-up answer resolve as a continuation
(see the refund-order-ID example in `triage_service.SYSTEM_PROMPT`). Planned
code-level invariant, not yet implemented: the complex-case node must reject
an actions list containing both a refund and a return for the same
`order_id`, rather than relying on the prompt alone.

**Verified:** all six simple intents (`order_status`, `price_check`,
`policy_question`, `return_request`, `refund_request`, `chitchat`) round-
tripped through `POST /support/message` unchanged, `policy_question` still
returned citations, and a previously-composite message ("Where's my order,
and what's your return policy if it arrives broken?") classified as
`complex_case` and routed to `END` cleanly (no crash) — expected, since the
complex-case node doesn't exist yet.

---

## Phase 9 — Complex-case ReAct loop

**Structural choice:** ReAct via `langchain.agents.create_agent` (or
`langgraph.prebuilt.create_react_agent`, per installed langchain version)
rather than a hand-rolled while-loop. Rationale: LangGraph/LangChain is a
de facto standard at this point; hand-rolling the exact thing the
framework does well teaches less than knowing how to configure and
reason about it — comparable to choosing Retrofit over a hand-rolled
HttpURLConnection client. This is a deliberate "framework vs
hand-rolled" data point (Section 4), distinct from Phase 5's triage,
which was hand-rolled first before moving into LangGraph.

**Tool loading:** via `langchain_mcp_adapters.client.MultiServerMCPClient
.get_tools()` against the existing Phase 7 MCP server (same HTTP
transport, same shared bearer token), not hand-written `@tool` wrappers.
Rejected hand-writing wrappers because it means two hand-maintained
descriptions of the same tool (MCP registration + LangChain wrapper)
that can silently drift. `get_langchain_tools()` lives in
`mcp_client/client.py` alongside the existing raw `call_tool()` path —
both coexist, serving different callers (deterministic nodes use
`call_tool` directly; the agent loop uses the LangChain-wrapped set).

**Tool result unwrapping — confirmed necessary, not automatic.**
`get_tools()` does not return clean Python objects. List-returning MCP
tools come back as one MCP content block per list item, each with the
payload JSON-encoded inside `text`. A shared `unwrap_tool_result` helper
(`mcp_server/utils/`) handles this consistently. Separately, empty
results (`[]`) were found to collapse to a blank string when serialized
into the model's prompt (`Tool:` with nothing after it) — a
`get_safe_langchain_tools()` wrapper coerces empty tool output to a
legible `"[]"` string before the model ever sees it.

**Terminal decision mechanism — resolved after significant debugging.**
Initially used `response_format=ToolStrategy(ComplexCaseResolution)`.
This forces `tool_choice="required"` on every turn, including the final
one — which is fundamentally in tension with a thinking-capable model
(the same collision LangChain's own docs describe for Anthropic:
"Thinking may not be enabled when tool_choice forces tool use").
Observed symptom: the model would investigate correctly, reason to the
right answer, then fail to invoke the terminal tool — instead writing a
well-formed JSON answer as plain text in `content`, sometimes repeating
it until hitting the token cap. Confirmed via direct comparison: the
same message given to the bare model in LM Studio's chat (no forced
tool_choice) correctly asked a clarifying question in one shot.

**Root cause, ultimately:** the underlying model
(`qwen3.5-9b-claude-4.6-opus-reasoning-distilled-v2`) has broken
thinking/content boundary parsing in this configuration — a known,
reported issue for small Qwen3.5 checkpoints on LM Studio specifically.
Multiple request-level fixes were attempted and failed to hold
(`chat_template_kwargs.enable_thinking`, LM Studio's `reasoning: "off"`
field) — `reasoning_tokens` stayed nonzero across attempts, confirming
neither flag was reaching the model's chat template.

**Fix applied:** edited the model's Jinja prompt template directly in LM
Studio (`{% set enable_thinking = false %}`), then reloaded the model.
This structurally prevents the model from ever entering a thinking
state, rather than asking the server to suppress it per-request — a
template-level fix, not a runtime flag, which is why it held where the
others didn't.

**Also resolved along the way, independent of the thinking issue:**
- `ComplexCaseResolution`'s Pydantic class needed a docstring — `Field(description=...)` on
  individual properties does not populate the tool's own top-level
  description, and a model under `tool_choice="required"` reliably
  avoided the one tool it had zero information about (i.e. the only way
  to terminate the loop).
- System prompt needed explicit statement of a real limitation ("no
  tool to look up a customer's orders by name/description — only by
  exact order_id") rather than an abstract "stop if you can't make
  progress" instruction, which a smaller model did not reliably act on.
- `recursion_limit=15` on `agent.ainvoke()` — no guard existed
  previously; a broken loop would run indefinitely.
- `max_tokens=1024` on the model — caps a single runaway generation
  (observed hitting `finish_reason: "length"` while repeating the same
  answer) rather than letting it run unbounded.

**Deferred to Phase 12 (evals):** further system-prompt tuning. Phase 9
ReAct is considered functionally complete; remaining prompt refinement
is measurement-driven work that belongs with the eval suite, not
further ad-hoc iteration now.

**Approval-gate integration — unchanged from earlier decision.** The
agent calls `create_approval_tool` / `initiate_return_tool` directly,
mid-loop, as ordinary tools — not a node-side deterministic replay.
`execute_refund` (the only thing that actually moves money) remains
unreachable by the agent regardless, so this doesn't weaken the
approval invariant; it's simply less code than reconstructing the
approval from the loop's tool-call history after the fact.

---

## Model serving: migration from LM Studio to vLLM

**Decision:** Replaced LM Studio with vLLM (self-hosted, WSL2 + CUDA
13.0, RTX 5070 Ti) as the local inference backend.

**Why:** LM Studio's GUI didn't expose K/V cache quantization control
or arbitrary llama.cpp flags (confirmed via open LM Studio bug tracker
issues, not just a config gap on our end), and its llama.cpp-based
Qwen3 reasoning/tool-call parsing was community-patched and fragile.
vLLM ships model-specific reasoning/tool-call parser code
(`--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`)
maintained directly by the vLLM/Qwen teams alongside model releases —
a materially more solid foundation for the agent-loop and structured-
output work in Phases 9-10.

**Model:** `RedHatAI/Qwen3.5-9B-quantized.w4a16` (W4A16, Red Hat/Neural
Magic via `llm-compressor`) chosen over raw bf16 (19.3GB weights alone,
doesn't fit 16GB VRAM) and over GGUF (vLLM's GGUF support is
deprecated to an out-of-tree plugin, unverified for Qwen3.5's hybrid
GDN architecture — not worth stacking on top of an already-bleeding-
edge model/GPU combination).

**KV cache dtype:** left at default (bf16), not fp8. Confirmed open
vLLM bug (#37554): dynamic FP8 KV cache silently corrupts output on
Qwen3.5's hybrid GDN+attention architecture (mismatched head dims
between linear-attention and full-attention layers) — no error thrown,
just bad output. Revisit only if a validated fix lands upstream.

**Reasoning + structured output collision (the core finding):**
grammar-constrained JSON (`response_format=json_schema` /
`instructor`'s `Mode.JSON_SCHEMA`) forces the model into schema-valid
output from token one, so it never emits `</think>`. vLLM's reasoning
parser then classifies the entire (correct) output as `reasoning`,
leaving `content=None` — this is a documented, acknowledged tension in
vLLM itself, not a bug in our code or schema.

- `triage_node`: fixed by disabling thinking entirely for this call
  (`chat_template_kwargs: {"enable_thinking": False}`) — correct
  architecturally regardless, since triage is a fast classification
  task with no need for reasoning (matches the plan's existing
  "cheap model for triage" line).
- `complex_case_node`: **not** disabling thinking here — this is the
  node that needs it. Works via LangChain's `ToolStrategy`, which
  extracts structured output through the tool-call parser rather than
  raw grammar constraint. Qwen3.5+ models legitimately start tool
  calls inside an open `<think>` block without closing it first
  (documented parser behavior) — `ToolStrategy` accommodates this by
  construction, `response_format=json_schema` does not. Verified
  end-to-end on the canonical "broken zipper" test case: multi-step
  tool loop, correct approval-queue halt, correct refund policy
  citation, correct historical-return context.

**`thinking_token_budget`: deliberately not used on `complex_case`.**
Open vLLM issue (#44676) confirms budget enforcement can force-inject
the reasoning-end token into the middle of in-progress tool-call
arguments on Qwen3.5+, corrupting them. Real risk outweighs the
runaway-reasoning problem it would solve, given tool calls are core to
this node's job. Candidate for triage-only use later if ever needed,
since triage has no tool calls.

**Sampling params:** set per-node from Qwen's official recommended
profiles, not left at defaults — `presence_penalty=1.5` in particular
is a documented, deliberate countermeasure to Qwen3.5's known
repetition/looping tendency, which we reproduced live (~6,900-token
spiral on a trivial 5-word constraint prompt). Split across
`ChatOpenAI` top-level kwargs (temperature/top_p/presence_penalty) and
`model_kwargs.extra_body` (top_k/min_p/repetition_penalty — vLLM
extensions, not standard OpenAI fields).

**Known open issue, not fixed:** refund/approval resolution is not yet
consistently accurate across runs — same class of problem already
flagged in the Phase 10 handoff (`resolve_from_observations`
occasionally narrating unbacked actions). `ToolStrategy` appears to
help but does not fully resolve it. Deliberately not chased further
now — this is exactly what Phase 12 evals exists to quantify, not
something to hand-tune against a handful of manual tests.


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
