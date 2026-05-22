# Platform Module Map

This repository is organized as a product monorepo with clear boundaries between the operational core, orchestration runtime, AI services, and enterprise integrations.

## Module Breakdown

### 1. `apps/api`

Production backend for:

- API gateway
- tenant-aware authentication hooks
- RBAC enforcement
- workflow management
- approvals
- audit trails
- orchestration runtime
- AI and policy services
- connector dispatch

### 2. `apps/api/app/core`

Cross-cutting platform concerns:

- environment settings
- security and principal resolution
- role checks

### 3. `apps/api/app/domain`

Core product entities and request/response schemas:

- workflows
- approvals
- extracted requests
- policy results
- audit records

### 4. `apps/api/app/db`

Persistence abstractions and adapters.

Current implementation:

- PostgreSQL workflow and audit repositories
- in-memory repositories retained for development/test mode
- Redis queue and job coordination

Planned implementation:

- tenant-scoped query helpers and repository guardrails
- operational reporting views and retention policies

### 5. `apps/api/app/orchestration`

Runtime engine that advances workflow state through:

- extraction
- policy evaluation
- approval branching
- completion and rejection
- internal agent execution

### 6. `apps/api/app/ai`

AI-facing services for:

- request extraction
- routing hints
- policy reasoning handoff

Current implementation uses deterministic local heuristics so the platform can be developed before wiring live model calls.

### 7. `apps/api/app/integrations`

Enterprise connector layer.

Current implementation:

- base connector contract
- connector registry
- Slack approval payload dispatch
- Gmail and Jira stubs ready for real vendor integrations

### 8. `apps/api/app/observability`

Operational telemetry for:

- request counting
- request latency snapshots
- recent-request inspection via internal API

### 9. `apps/web`

Next.js operations console for:

- module visibility
- workflow monitoring
- approval UI
- operator navigation

### 10. `docker-compose.yml`

Local stack with:

- PostgreSQL
- Redis
- FastAPI API
- Next.js web

## Remaining Production SaaS Gaps

The core workflow engine is in place, but the platform still needs the following for a production-grade, scalable SaaS release:

- request tracing, request metrics, and operational dashboards
- real Slack, Gmail, and Jira connectors with retries and failure handling
- tenant-safe reporting endpoints and stronger row-level isolation guarantees
- web console workflows for approvals, audit review, and document search
- usage limits, quota enforcement, and billing hooks
- background job dead-letter inspection and replay tooling
- customer-facing admin settings for tenants, users, roles, and connector configuration

## Build Strategy

The repo starts with a vertical slice across every layer instead of building one giant module at a time. That gives us a usable backbone for expansion:

1. intake
2. extraction
3. policy decision
4. approval creation
5. audit logging
6. connector dispatch
7. workflow completion

