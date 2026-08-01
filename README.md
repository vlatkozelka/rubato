# Rubato

An AI customer support copilot for a fictional e-commerce store — built to
exercise, end to end, the concepts that show up on real AI engineer job
descriptions: structured output, tool calling, MCP, RAG (with hybrid search
and reranking), agent loops (ReAct and plan-and-execute), memory, guardrails,
evals, tracing, and a small LoRA fine-tune, all measured rather than assumed.

Full build plan and rationale: see `PLAN.md`. Decisions made along the way,
and why: see `DECISIONS.md`. Eval results: see `EVALS.md` (from Phase 12 on).

**Status: Phase 5 in progress (LangGraph wiring).** Triage, structured
lookups, and RAG are wired into a graph. Sandbox data now lives in Postgres
(not JSON files), and staff/customer JWT auth is in place — see
`DECISIONS.md` for the infra-detour writeup. A minimal customer login +
chatbot UI now sits on top of that auth (see "Customer UI" below), also
written up in `DECISIONS.md`.

## Quick start

Requires [LM Studio](https://lmstudio.ai) running locally with a model loaded
and the local server started (default port 1234), and Docker for Postgres.

```bash
docker compose up db --build
```

This starts Postgres and seeds it from the SQL scripts in `db/init/` —
schema and data both, including seeded staff/customer login accounts. Then
run the app locally (see "Running without Docker" below); the `app` service
in `docker-compose.yml` is unmaintained scaffolding, not the working path.

Log in to get a token, then call the endpoints with it:

```bash
curl http://localhost:8000/health

# Customer login (seeded demo accounts — see db/init/006_seed_customers.sql)
curl -X POST http://localhost:8000/auth/customer/login \
  -H "Content-Type: application/json" \
  -d '{"email": "marcus.ito@example.com", "password": "customer-demo-pass"}'
# -> {"access_token": "...", "token_type": "bearer", "expires_in": 3600}

curl -X POST http://localhost:8000/support/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"conversation_id": "c1", "message": "Where is my order?"}'

# Staff login (separate endpoint/service — see db/init/012_seed_staff_users.sql),
# for the approval queue
curl -X POST http://localhost:8000/auth/staff/login \
  -H "Content-Type: application/json" \
  -d '{"email": "staff@rubato.test", "password": "staff-demo-pass"}'

curl http://localhost:8000/approvals -H "Authorization: Bearer <staff_access_token>"
```

`customer_id` is derived from the token, not passed in the request body —
see `DECISIONS.md`.

## Customer UI

With the app running (see below), open **http://localhost:8000/** in a
browser — it redirects to `/login`. Log in with any seeded customer email
(`db/init/006_seed_customers.sql`) and password `customer-demo-pass`; on
success you land on `/chat`, a minimal chat UI that calls
`POST /support/message` with the JWT attached. "Log out" clears the token
and returns to `/login`; visiting `/chat` without a valid token bounces you
back there too.

Static, no build step — plain HTML/CSS/vanilla JS served directly by
FastAPI (`static/`). See `DECISIONS.md` for the stack choice and
token-storage tradeoff.

## Staff UI

Open **http://localhost:8000/admin** — a separate login page from the
customer one, backed by `POST /auth/staff/login` and the `staff_users`
table (`db/init/011_create_staff_users.sql`), not the customer table. Log
in with `staff@rubato.test` / `staff-demo-pass`; on success you land on
`/admin/dashboard`, which lists pending refund approvals (calling the
existing `GET /approvals`, with Approve/Deny buttons wired to
`POST /approvals/{id}/approve` and `/deny`) and an editable product table
(`GET /products`, `PATCH /products/{id}`).

The staff JWT carries `role: staff` (issued the same way as the customer
`role: customer` token — same `create_access_token`, same
`Authorization: Bearer` header, same `sessionStorage` mechanics, just
under its own key `rubato_staff_token` so the two never collide in the
same browser tab) and is checked by `require_staff` on every admin/staff
endpoint, so a customer token is rejected (403) by staff endpoints and a
staff token is rejected by customer endpoints (e.g. `/support/message`)
— see `app/auth.py`. Visiting `/admin/dashboard` without a valid staff
token bounces you back to `/admin`, same pattern as `/chat`.

### Running without Docker

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires `POSTGRES_DSN` pointing at a running Postgres instance (defaults to
the docker-compose one on `localhost:5432`) and a `JWT_SECRET_KEY` set for
anything beyond local dev — see `app/config.py`.

## Project layout

```
app/            FastAPI app, config, auth, (later) graph/agent code
db/init/        Numbered SQL: schema + seed data, run automatically on first
                Postgres container init
docs/           Store policy docs used for RAG (includes a deliberate
                contradiction between return-policy.md and warranty.md)
models/         Pydantic models (one per file)
services/       Postgres-backed data access + business logic (one per file)
static/         Customer login + chat UI — static HTML/CSS/vanilla JS,
                served directly by FastAPI, no build step
tests/          Eval suite and unit tests (from Phase 12); a few validate_*.py
                scripts exercise services directly against the seeded DB
```

## Why this domain

Customer support for e-commerce is boring on purpose — instantly legible to
any interviewer, and it naturally requires structured lookups, grounded
retrieval, tool use, multi-step reasoning, and a real human-approval gate
without any contrivance. The domain isn't the point; the architecture is.
