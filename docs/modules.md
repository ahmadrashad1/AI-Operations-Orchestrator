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

- in-memory repositories for fast iteration

Planned implementation:

- PostgreSQL workflow and audit repositories
- Redis queues and locks

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
- Slack approval payload dispatch stub

### 8. `apps/web`

Next.js operations console for:

- module visibility
- workflow monitoring
- approval UI
- operator navigation

### 9. `docker-compose.yml`

Local stack with:

- PostgreSQL
- Redis
- FastAPI API
- Next.js web

## Build Strategy

The repo starts with a vertical slice across every layer instead of building one giant module at a time. That gives us a usable backbone for expansion:

1. intake
2. extraction
3. policy decision
4. approval creation
5. audit logging
6. connector dispatch
7. workflow completion

