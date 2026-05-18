# Production implementation backlog and module sequence

This document extracts **what is still missing** for production-grade automation relative to `BUILD_PLAN.md`, reconciled with the **current codebase** (PostgreSQL, Redis queue, JWT validation, LangGraph-style runtime, and LLM extraction scaffolding exist; connectors and operators layer remain thin).

## Not yet production-grade (extracted backlog)

### Automation & integrations

- **Connector dispatch worker**: Jobs are written to Redis but **no long-running consumer** was shipping dispatches end-to-end; approvals queued without guaranteed delivery.
- **Real Slack delivery**: Connector still returned a **stub “queued”** payload instead of calling Incoming Webhooks (or Web API) with retries at execution time.
- **Inbound Slack interactions**: No signed callback route for approve/reject buttons (`BUILD_PLAN` Phase 3.1).
- **Gmail / Jira**: Still **stubs**; no SMTP/API or Jira REST flows.

### Identity & governance

- **Auth issuance API**: JWT **verification** exists; **login / refresh** HTTP routes and password-backed identities were not wired.
- **RBAC depth**: `require_roles` only; no permission matrix / `@require_permission` as specified in the build plan.
- **Token revocation**: Blacklist table exists; **check on each request** not wired.

### Platform operations

- **Observability**: `telemetry.py` / worker queue stubs are placeholders — no Prometheus `/metrics`, OTEL, or structured logging to sinks.
- **Readiness probes**: `/readyz` does not verify DB/Redis.
- **Docker / K8s**: Compose lacked a **worker** service and **Redis persistence**; no Kubernetes manifests from Phase 5.

### Web console

- **Operations UI**: Next.js remains a **marketing/module scaffold** — no login, workflow list/detail, approval UI, audit timeline, or WebSockets.

### Quality & optional AI scope

- **Coverage targets, E2E Playwright, load/security suites** as in Phase 5.2.
- **RAG / pgvector / Salesforce / ERP** — optional tranches from the original plan.

---

## Sequential modules (execution order)

| Order | Module | Goal |
|-------|--------|------|
| **M1** | Async dispatch worker | Dedicated process consumes `connector_dispatch` jobs and performs real Slack webhook POSTs with failure → Redis retry/DLQ semantics already in `RedisJobQueue`. |
| **M2** | Auth issuance | `PostgresUserRepository`, `POST /auth/login`, `POST /auth/token/refresh`, JWT claim decoding fixes for standard `exp` integers. |
| **M3** | Concurrency safety | Redis distributed lock around approval mutations in production when Redis is healthy. |
| **M4** | Compose hardening | `worker` service + Redis volume; API/worker share env. |
| **M5** | (Next) Observability | `/metrics`, structured logs, readiness checks — not started in this pass. |
| **M6** | (Next) Web console | Login + workflows + approvals wired to API. |

## Implementation status

- **M1–M4**: Implemented in the repository alongside this document unless noted otherwise in review.
- **M5–M6**: Planned next (observability, then web console).

### Operational notes (auth)

- `POST /api/v1/auth/login` and `/api/v1/auth/token/refresh` require PostgreSQL (`ServiceContainer.user_repository`). Seed at least one row in `users` with `hashed_password` from `app.core.auth.hash_password`.
- Development callers can still use `x-user-id` / `x-tenant-id` / `x-roles` when no `Authorization` header is sent (`HTTPBearer(auto_error=False)`).
