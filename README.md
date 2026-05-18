# AI Operations Orchestrator

Enterprise-grade AI-native orchestration platform for coordinating workflows across people, systems, policies, and agents.

## Workspace Layout

- `apps/api`: FastAPI gateway, orchestration runtime, AI services, policy engine, and connector interfaces.
- `apps/web`: Next.js operations console for workflow visibility and approvals.
- `docs`: architecture and module map.
- `docker-compose.yml`: local development stack with PostgreSQL, Redis, API, and web.

## Implemented First Slice

- Workflow intake API: `POST /api/v1/workflow/create`
- Workflow lookup API: `GET /api/v1/workflow/{workflow_id}`
- Approval response API: `POST /api/v1/approval/respond`
- Internal execution APIs for agents and events
- In-memory repositories that can be swapped with PostgreSQL and Redis adapters
- Procurement extraction, deterministic policy evaluation, approval routing, audit logging, and Slack-style approval dispatch payloads
- Operations dashboard scaffold in Next.js

## CI/CD

- CI workflow: `.github/workflows/ci.yml`
- CD workflow: `.github/workflows/cd-containers.yml`
- Dependency update automation: `.github/dependabot.yml`

The CI pipeline runs:

1. Python compile, lint, and API tests
2. Node install, typecheck, and Next.js build
3. Docker smoke builds for both runtime images

The CD pipeline publishes versioned container images to GHCR on pushes to `main`, semantic version tags like `v1.0.0`, or manual dispatch.

## Next Build Steps

1. Replace in-memory repositories with PostgreSQL and Redis adapters.
2. Add real auth, JWT issuing, tenant-aware RBAC, and OAuth SSO.
3. Replace the local orchestration runtime with persisted LangGraph execution.
4. Add vector retrieval, document ingestion, and policy knowledge management.
5. Connect Slack, Gmail, Jira, Salesforce, and ERP providers with real credentials and retries.
