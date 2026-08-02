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
