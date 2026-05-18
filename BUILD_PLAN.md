# AI Operations Orchestrator - Comprehensive Build Plan

## Executive Summary

The AI Operations Orchestrator has completed a **first-slice MVP** with core workflow, approval, and audit functionality using in-memory storage and deterministic AI. This plan outlines the roadmap to production-grade enterprise platform with real databases, live LLM integration, production authentication, real connectors, and a full operations console.

**Timeline**: 7-9 weeks | **Phases**: 5 | **Priority Areas**: Database, Auth, LLM, Connectors, Web UI

---

## Current Implementation Status

### ✅ What's Implemented (MVP First Slice)

#### API Core
- **FastAPI Gateway** with tenant-aware routing
- **Workflow Endpoints**: POST `/api/v1/workflow/create`, GET `/api/v1/workflow/{workflow_id}`
- **Approval Endpoints**: POST `/api/v1/approval/respond`
- **Internal Endpoints**: Agent execution and event processing APIs
- **Health Checks**: Basic service health endpoint

#### Orchestration Engine
- **Request Extraction**: Deterministic regex + heuristic parser
  - Recognizes: laptops, monitors, licenses, vendors from request text
  - Calculates cost based on price book
  - Extracts department, urgency, category
- **Policy Engine**: Rule-based evaluation
  - Manager approval threshold: $3,000
  - Finance approval threshold: $5,000
  - Special handling for services and urgent requests
- **Approval State Machine**: In-memory workflow state
  - Pending → Approved/Rejected transitions
  - Multi-stage approval orchestration
  - Audit trail logging

#### Persistence (In-Memory)
- `WorkflowRepository`: Thread-safe dict with RLock
- `AuditRepository`: Append-only log with RLock
- Suitable for development/testing, not production

#### Authentication (Header-Based)
- Development mode: Accepts `x-user-id`, `x-tenant-id`, `x-roles` headers
- No JWT validation, token expiry, or OAuth
- Tenant isolation via header only (not enforced in queries)

#### Connectors (Stubs)
- **SlackApprovalConnector**: Returns queued payload, doesn't send real messages
- **GmailConnector**: Stub for email dispatch
- **JiraConnector**: Stub for ticket creation
- No real credentials, API calls, or retry logic

#### Web Frontend
- **Next.js 15** with React 19
- Minimal scaffold: module list component
- No approval UI, workflow list, or real API integration

#### Infrastructure
- **Docker Compose**: Postgres, Redis, FastAPI, Next.js definitions
- **CI/CD**: GitHub Actions for lint, test, container builds
- No Kubernetes, no observability stack

---

## 🔴 Phase 1: Core Infrastructure (High Priority)
**Duration**: 1-2 weeks | **Objective**: Production-ready storage and authentication

### 1.1 PostgreSQL Migration

**Dependency**: Everything else depends on this

#### Tasks
- [ ] Add dependencies to `pyproject.toml`:
  - `sqlalchemy>=2.0.0`
  - `psycopg>=3.1.0`
  - `alembic>=1.14.0`
  - `sqlalchemy-utils>=0.41.0`
- [ ] Refactor `app/db/repositories.py` to use abstract base classes
  - Extract interface methods: `create()`, `update()`, `get()`, `list()`
  - Keep `WorkflowRepository` and `AuditRepository` as abstract interfaces
- [ ] Create `app/db/models.py`:
  - Define SQLAlchemy ORM models for `WorkflowState`
  - Define `AuditLogRecord` model with JSON columns for extraction/policy
  - Add indexes on workflow_id, tenant_id, created_at, status
- [ ] Create `app/db/postgres.py`:
  - Implement `PostgresWorkflowRepository(WorkflowRepository)`
  - Implement `PostgresAuditRepository(AuditRepository)`
  - Add connection pooling with sqlalchemy.pool.QueuePool
- [ ] Set up Alembic migrations:
  - Create `alembic/` folder structure
  - Write initial migration: `001_create_workflows_audit.py`
  - Add migration runner to bootstrap
- [ ] Update `app/bootstrap.py`:
  - Load DB_URL from config
  - Create SQLAlchemy engine with connection pool
  - Swap in-memory repos with Postgres repos
- [ ] Update `docker-compose.yml`:
  - Ensure postgres service has persistent volume
  - Add health check for postgres readiness

**Success Criteria**:
- Workflows persist across app restarts
- Audit logs persist correctly
- Tenant data is isolated at database level (queries filter by tenant_id)
- Tests pass with testcontainers postgres

---

### 1.2 Redis Queue & Distributed Locks

**Dependency**: Enables reliable async dispatch, required for Slack/Gmail real dispatch

#### Tasks
- [ ] Add dependencies to `pyproject.toml`:
  - `redis>=5.0.0`
  - `aioredis>=2.0.1`
- [ ] Create `app/services/queue.py`:
  - `RedisJobQueue` class with `.enqueue()` and `.dequeue()`
  - Implement job serialization (JSON)
  - Add TTL for expired jobs
- [ ] Create `app/core/locks.py`:
  - Implement distributed lock for workflow state mutations
  - Use Redis SETNX + Lua for atomic operations
  - Add lock timeout and automatic release
- [ ] Update `app/orchestration/runtime.py`:
  - Wrap `process_approval_response()` with distributed lock
  - Replace direct connector dispatch with queue.enqueue()
  - Add job tracking and status polling
- [ ] Create background worker service `app/workers/dispatcher.py`:
  - Poll job queue every 5 seconds
  - Execute connector.execute() for each job
  - Implement retry logic: exponential backoff (2s, 4s, 8s... max 5 retries)
  - Move failed jobs to dead letter queue
  - Update audit log on dispatch success/failure
- [ ] Update `docker-compose.yml`:
  - Add Redis service with persistent volume
  - Set maxmemory policy to allkeys-lru
- [ ] Add worker process to Docker image

**Success Criteria**:
- Approval dispatch is asynchronous and non-blocking
- Retries happen automatically with backoff
- Failed dispatches are tracked and retrievable
- Tests verify queue behavior with Redis testcontainers

---

### 1.3 Real Authentication (JWT + OAuth)

**Dependency**: Required for multi-tenant, production deployments

#### Tasks
- [ ] Add dependencies:
  - `python-jose>=3.3.0`
  - `passlib>=1.7.4`
  - `python-multipart>=0.0.6`
- [ ] Create `app/core/auth.py`:
  - Implement `create_jwt_token(user_id, tenant_id, roles, expires_delta)`
  - Implement JWT validation and extraction
  - Add token refresh logic
  - Use HS256 or RS256 with configurable secret
- [ ] Create `app/api/auth.py`:
  - POST `/api/v1/auth/login`: username/password → JWT token
  - POST `/api/v1/auth/token/refresh`: refresh_token → new JWT
  - POST `/api/v1/auth/oauth/callback`: Handle OAuth redirects
- [ ] Update `app/core/security.py`:
  - Replace header-based principal resolution with JWT bearer token
  - Create `get_current_principal()` dependency that validates JWT
  - Add scope-based authorization checks
  - Enforce tenant_id isolation: principal can only access own tenant resources
- [ ] Create `app/core/rbac.py`:
  - Define role hierarchy: Admin > Manager/Finance > Employee > Auditor
  - Implement permission matrix for endpoints
  - Add `@require_permission("workflow:create")` decorator
- [ ] Update all route dependencies:
  - Replace `require_roles()` calls with permission-based checks
  - Update test helpers to generate valid JWTs
- [ ] Add `app/models/user.py`:
  - User model: user_id, email, hashed_password, roles, tenant_id
  - Create migration for users table
  - Add password hashing utilities

**Success Criteria**:
- JWT tokens are validated on all endpoints
- Tokens expire after 1 hour (configurable)
- Refresh tokens allow renewal without re-login
- Users cannot access other tenants' data
- Audit logs include authenticated user context
- Header-based auth is removed

---

## 🟡 Phase 2: AI/LLM Integration (Medium Priority)
**Duration**: 1 week | **Objective**: Live AI extraction and dynamic policy reasoning

### 2.1 LangGraph Orchestration

**Dependency**: Foundation for stateful multi-step workflows

#### Tasks
- [ ] Add dependencies:
  - `langgraph>=0.1.0`
  - `langsmith>=0.1.0`
  - `langchain>=0.2.0`
- [ ] Create `app/orchestration/graph.py`:
  - Define workflow state schema with extraction, policy, approvals fields
  - Create StateGraph with nodes:
    - `node_extract`: Call RequestExtractionAgent
    - `node_policy`: Call PolicyEngine
    - `node_build_approvals`: Build ApprovalRecord list
    - `node_dispatch`: Queue connector dispatch jobs
  - Add conditional edges for approval branching
  - Add node for approval response handling
- [ ] Update `WorkflowRuntime.bootstrap()`:
  - Instead of sequential function calls, invoke LangGraph workflow
  - Pass extracted/policy results through graph context
  - Collect execution trace for debugging
- [ ] Add LangSmith integration (optional):
  - Log workflow executions to LangSmith for visibility
  - Create dashboard link in audit UI
- [ ] Create tests for graph execution paths

**Success Criteria**:
- Workflows execute via LangGraph state machine
- Workflow state is persisted at each step
- Execution traces are captured and queryable
- Graph visualization works in LangSmith console

---

### 2.2 Real LLM Extraction (e.g., GPT-4 or Claude)

**Dependency**: Replace deterministic extraction with foundation model

#### Tasks
- [ ] Add dependencies:
  - `openai>=1.0.0` OR `anthropic>=0.1.0`
- [ ] Create `app/ai/llm_extraction.py`:
  - Implement `RequestExtractionAgent.extract_with_llm(request_text, extraction_schema)`
  - Use structured output (JSON mode) to ensure valid parsing
  - Prompt template:
    ```
    Extract procurement request details:
    - item_name, category, quantity, estimated_unit_cost, urgency, department
    
    Request: {request_text}
    
    Respond with valid JSON.
    ```
  - Add retry logic for LLM failures (fallback to deterministic)
  - Log LLM cost for billing/monitoring
- [ ] Create `app/ai/schemas.py`:
  - Define Pydantic schemas for extraction output
  - Use `model_json_schema()` for prompt injection protection
- [ ] Update `RequestExtractionAgent`:
  - Add `use_llm: bool` flag (configurable)
  - Try LLM extraction, fall back to heuristic on error
  - Cache extraction results by request_text hash (Redis)
  - Add cost tracking
- [ ] Add caching layer:
  - Store extraction results in Redis with 24hr TTL
  - Skip LLM call for duplicate requests
- [ ] Update tests:
  - Mock LLM for unit tests
  - Add integration tests against real LLM (marked @slow)
  - Test fallback behavior on LLM failure

**Success Criteria**:
- Extraction handles complex, natural language requests
- LLM calls are cached to reduce cost and latency
- Fallback to deterministic extraction works reliably
- Cost tracking shows LLM usage
- Tests verify output schema compliance

---

### 2.3 Vector Retrieval & RAG (Optional, Advanced)

**Dependency**: Add semantic policy knowledge base

#### Tasks
- [ ] Add dependencies:
  - `pgvector>=0.2.0`
  - `langchain-postgres>=0.2.0`
  - `openai>=1.0.0` (for embeddings)
- [ ] Create vector storage in PostgreSQL:
  - Add pgvector extension to postgres
  - Create documents table with embedding vector column
  - Add similarity search indexes
- [ ] Create `app/ai/retrieval.py`:
  - `DocumentRetrieval` class with `.index_document()` and `.search(query)`
  - Use OpenAI embeddings (text-embedding-3-small)
  - Return top-5 most similar documents
- [ ] Create document ingestion endpoint:
  - POST `/api/v1/documents/upload`: Accept PDF/TXT files
  - Parse and chunk documents (512-token chunks with overlap)
  - Generate embeddings and index
  - Store metadata: source, date, category
- [ ] Update PolicyEngine:
  - Retrieve relevant policy documents via RAG
  - Include retrieved context in LLM prompt for policy evaluation
  - Allows dynamic, knowledge-based policy rules
- [ ] Add document management UI:
  - List indexed documents
  - Search documents by keyword
  - View document chunks and similarity scores

**Success Criteria**:
- Policy knowledge base is searchable by semantic similarity
- Policy engine uses retrieved documents to inform decisions
- Document upload and indexing work reliably
- Retrieval improves policy rule relevance over time

---

## 🟠 Phase 3: Enterprise Integrations (Lower Priority)
**Duration**: 1-2 weeks | **Objective**: Real external system connectivity

### 3.1 Slack Real Integration

**Current State**: Stub returns queued payload

**Tasks**:
- [ ] Implement `SlackApprovalConnector.execute()` with real API:
  - POST to slack_webhook_url with formatted message
  - Include workflow details, approvers, decision buttons
  - Add message thread for conversation
- [ ] Add Slack interactive components:
  - Button interactions: "Approve" / "Reject"
  - Callback URL: POST `/api/v1/integrations/slack/callback`
  - Verify webhook signatures (HMAC-SHA256)
  - Parse callback payload and call `approval_service.respond()`
- [ ] Add retry logic:
  - 3 retries with exponential backoff
  - Dead letter queue for failed sends
  - Alert on repeated failures
- [ ] Testing:
  - Mock Slack API for unit tests
  - Add integration test with Slack test workspace (optional)

**Success Criteria**:
- Approval requests appear in Slack with interactive buttons
- Slack responders' decisions sync back to workflow
- Failed sends are retried and tracked

---

### 3.2 Gmail Integration

**Tasks**:
- [ ] Add dependencies:
  - `python-dotenv>=1.0.0`
  - Google OAuth2 support or SMTP + OAuth
- [ ] Implement `GmailConnector.execute()`:
  - Build email template with workflow details
  - Send via SMTP or Gmail API
  - Include approval link with signed token
- [ ] Create approval link handler:
  - GET `/api/v1/approvals/link/{token}`: Pre-filled decision
  - Verify signature on token
  - Redirect to approval page with auto-filled data
- [ ] Add email retry and bounce tracking

**Success Criteria**:
- Approval emails sent to approvers
- Email links automatically fill in approval responses
- Bounced emails are tracked and alerted

---

### 3.3 Jira Integration

**Tasks**:
- [ ] Add Jira API client:
  - Authenticate with API token
  - Create issue from workflow: POST /rest/api/3/issues
  - Link issue to workflow (custom field or description)
- [ ] Create Jira issue on workflow creation:
  - Summary: Procurement Request: {item_name}
  - Description: Extracted details + approval chain
  - Link to orchestrator workflow in description
- [ ] Update Jira issue on approval:
  - Comment with approval status
  - Transition issue on completion (e.g., "Done")
- [ ] Bidirectional sync (optional):
  - Watch for Jira updates
  - Sync status back to orchestrator

**Success Criteria**:
- Workflows create Jira tickets automatically
- Approvals update Jira comments and status
- Jira issues link back to orchestrator workflows

---

### 3.4 Salesforce Integration (Optional)

**Tasks**:
- [ ] Salesforce OAuth2 connection
- [ ] Create Account/Opportunity from workflow
- [ ] Sync approval status to SFDC

---

### 3.5 ERP Integration (Optional)

**Tasks**:
- [ ] SAP/Oracle connector for PO creation
- [ ] General ledger posting on approval
- [ ] Vendor master sync

---

## 💜 Phase 4: Operations Console (Web UI)
**Duration**: 1-2 weeks | **Objective**: Full operations visibility and control

### 4.1 Authentication UI

**Tasks**:
- [ ] Create login page (`app/login/page.tsx`):
  - Email/password form
  - OAuth SSO buttons (Google, Azure AD, etc.)
  - Remember me checkbox
- [ ] Implement session management:
  - Store JWT in secure httpOnly cookie
  - Auto-refresh token before expiry
  - Logout: Clear cookie + invalidate token
- [ ] Add permission-based routing:
  - Guard routes by required permissions
  - Redirect unauthorized users to login
  - Show "Access Denied" message if lacking permission

---

### 4.2 Workflow Management UI

**Tasks**:
- [ ] Create workflow list page (`app/workflows/page.tsx`):
  - Table with columns: workflow_id, status, created_at, approvals_pending, actions
  - Pagination, sorting, filtering by status/date range
  - Search by workflow_id or department
  - Bulk actions: retry failed, cancel pending
- [ ] Create workflow detail page (`app/workflows/[id]/page.tsx`):
  - Display extracted request details
  - Show policy evaluation results
  - Display approval chain with status
  - Audit trail timeline
  - Related Jira/Slack links
- [ ] Create workflow creation form:
  - Textarea for request text
  - Departmentselection dropdown
  - Submit → POST /api/v1/workflow/create

---

### 4.3 Approval UI

**Tasks**:
- [ ] Create approval card component (`components/approval-card.tsx`):
  - Display approver name, status, due date
  - Show decision buttons: Approve / Reject / Delegate
  - Comment textarea
  - Show previous decisions
- [ ] Create approval modal:
  - Triggered when user clicks approve/reject
  - Confirmation + comment entry
  - Submit → POST /api/v1/approval/respond
- [ ] Add approval list view:
  - Show pending approvals assigned to current user
  - Filter by priority, due date
  - Quick approve/reject actions
  - Notification badge for new approvals

---

### 4.4 Audit & Monitoring Dashboard

**Tasks**:
- [ ] Create audit trail view:
  - Timeline of workflow events: extracted, policy evaluated, approved, completed
  - Expandable event details (JSON viewer)
  - Actor, timestamp, action log
- [ ] Create system dashboard:
  - Workflow metrics: created today, pending, completed
  - Approval latency (p50, p95, p99)
  - Connector success rates
  - Active users
  - Charts: workflow creation trend, approval time histogram
- [ ] Create admin panel:
  - Tenant management: create, list, delete
  - User management: create roles, assign permissions
  - System config: approval thresholds, timeout values
  - Log viewer: structured logs with search

---

### 4.5 Real-Time Updates (WebSocket)

**Tasks**:
- [ ] Add WebSocket support to FastAPI:
  - `/ws/workflows/{workflow_id}`: Subscribe to workflow updates
  - Broadcast approval responses to subscribed clients
  - Broadcast status changes
- [ ] Implement client-side WebSocket handler:
  - Auto-refresh workflow details on update
  - Push notification for new approvals
  - Real-time approval count updates

---

## 🟢 Phase 5: Observability & Production Readiness
**Duration**: 1-2 weeks | **Objective**: Monitoring, alerting, and operational excellence

### 5.1 Observability Stack

**Tasks**:
- [ ] Add OpenTelemetry:
  - `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-prometheus`
  - Instrument FastAPI app with automatic span creation
  - Export traces to Jaeger or Datadog
- [ ] Add Prometheus metrics:
  - Workflow creation rate (per tenant, per status)
  - Approval latency histogram
  - Connector dispatch success/failure rates
  - Database query duration
  - Redis operation duration
  - Expose `/metrics` endpoint
- [ ] Add structured logging:
  - Use Python `structlog` library
  - Add context: request_id, user_id, tenant_id, workflow_id
  - Send logs to ELK/Loki/Datadog
  - JSON format for log aggregation
- [ ] Add error tracking:
  - Sentry integration for exception tracking
  - Create alerts for critical errors
  - Link errors to transactions for context

---

### 5.2 Testing & Quality

**Tasks**:
- [ ] Unit tests:
  - Target: 80%+ code coverage
  - Mock external dependencies (LLM, connectors, Redis)
  - Test error paths and edge cases
- [ ] Integration tests:
  - Use testcontainers for Postgres, Redis
  - Test full workflow end-to-end
  - Test connector dispatch behavior
  - Verify database isolation per tenant
- [ ] E2E tests (Playwright):
  - Test login flow
  - Create workflow from UI
  - Approve workflow via UI
  - Verify audit trail
- [ ] Performance tests:
  - Load test: 1000 concurrent workflows
  - Measure workflow bootstrap latency
  - Benchmark extraction + policy evaluation
  - Identify bottlenecks
- [ ] Security tests:
  - SQL injection tests
  - JWT tampering attempts
  - Cross-tenant access attempts
  - CORS and CSRF validation

---

### 5.3 Deployment & Scaling

**Tasks**:
- [ ] Kubernetes manifests:
  - Deployment for FastAPI (replicas: 3, resources: requests/limits)
  - Deployment for worker processes
  - StatefulSet for Postgres backup
  - ConfigMap for settings, Secrets for credentials
  - Service discovery for internal APIs
  - Ingress for external API routing
- [ ] Helm charts (optional):
  - Parameterize deployments
  - Support multiple environments (dev, staging, prod)
  - Enable easy upgrades
- [ ] Blue-green deployment:
  - Gradual traffic shift to new version
  - Automatic rollback on errors
- [ ] Auto-scaling:
  - HPA based on CPU and request count
  - Scale worker pods by job queue depth
- [ ] Health checks:
  - Liveness probe: /health
  - Readiness probe: check DB/Redis connectivity
  - Startup probe: wait for migrations to complete
- [ ] Graceful shutdown:
  - Drain in-flight requests (30s timeout)
  - Stop accepting new jobs
  - Complete outstanding approvals before exit

---

### 5.4 Documentation

**Tasks**:
- [ ] API documentation:
  - OpenAPI/Swagger from FastAPI auto-generation
  - Document auth flow
  - Document webhook formats (Slack, Jira)
- [ ] Architecture documentation:
  - System diagram: API → Orchestration → Connectors
  - Data flow diagrams
  - Sequence diagrams for approval flow
- [ ] Operations runbooks:
  - Database migration procedure
  - Incident response playbooks
  - Scaling procedures
  - Backup/recovery procedures
- [ ] Developer guide:
  - Local development setup
  - Testing instructions
  - Contributing guidelines

---

## Sequencing & Dependencies

```
Phase 1 (Weeks 1-2)
├─ 1.1 PostgreSQL Migration ✓ (unblocks all data persistence)
├─ 1.2 Redis Queue ✓ (depends on 1.1)
└─ 1.3 Real Auth ✓ (parallel, no dependencies)

Phase 2 (Week 3)
├─ 2.1 LangGraph ✓ (depends on 1.1)
├─ 2.2 Real LLM Extraction ✓ (depends on 2.1)
└─ 2.3 RAG (optional, depends on 2.1)

Phase 3 (Weeks 4-5)
├─ 3.1 Slack ✓ (depends on 1.2)
├─ 3.2 Gmail ✓ (depends on 1.2)
└─ 3.3 Jira ✓ (depends on 1.2)

Phase 4 (Weeks 5-6)
├─ 4.1 Auth UI ✓ (depends on 1.3)
├─ 4.2 Workflow UI ✓ (depends on 4.1)
├─ 4.3 Approval UI ✓ (depends on 4.1)
└─ 4.5 WebSocket (optional, depends on 4.3)

Phase 5 (Week 7+)
├─ 5.1 Observability ✓ (can start in parallel)
├─ 5.2 Testing ✓ (ongoing, done in parallel)
└─ 5.3 Deployment ✓ (after Phase 1-3)
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM extraction hallucinations | High | Fall back to deterministic extraction, validate schema strictly |
| Connector API rate limits | Medium | Implement request queuing, exponential backoff, request coalescing |
| Multi-tenant data leaks | Critical | Add database-level tenant filters, audit all queries, penetration test |
| Redis data loss | Medium | Enable persistence (AOF), replicate to replica, monitor for failures |
| Workflow state corruption | High | Use distributed locks, idempotent operations, state machine validation |
| Performance under load | Medium | Benchmark early, use connection pooling, implement caching |

---

## Success Metrics

- [ ] Phase 1: Zero data loss on app restart; multi-user authentication working
- [ ] Phase 2: Extraction accuracy > 95%; policy rules execute via LangGraph
- [ ] Phase 3: All three connectors (Slack, Gmail, Jira) functioning; retry logic working
- [ ] Phase 4: Web UI displays workflows, approvals, audit trail; real-time updates working
- [ ] Phase 5: Traces visible in Jaeger; alerts firing on errors; K8s deployment stable

---

## File Changes Summary

### Backend (apps/api)
| File | Changes |
|------|---------|
| `pyproject.toml` | Add all dependencies from phases |
| `app/db/repositories.py` | Abstract base classes |
| `app/db/models.py` | NEW - SQLAlchemy ORM |
| `app/db/postgres.py` | NEW - PostgreSQL implementations |
| `app/db/migrations/` | NEW - Alembic migrations |
| `app/core/auth.py` | NEW - JWT/OAuth |
| `app/core/security.py` | Update for JWT validation |
| `app/core/rbac.py` | NEW - Role-based access control |
| `app/core/locks.py` | NEW - Distributed locks |
| `app/services/queue.py` | NEW - Job queue |
| `app/ai/llm_extraction.py` | NEW - LLM extraction |
| `app/ai/retrieval.py` | NEW - Vector RAG |
| `app/orchestration/graph.py` | NEW - LangGraph workflow |
| `app/integrations/slack.py` | Replace stub with real API |
| `app/integrations/gmail.py` | Replace stub with real API |
| `app/integrations/jira.py` | Replace stub with real API |
| `app/workers/dispatcher.py` | NEW - Background job worker |
| `app/observability/` | NEW - Tracing, metrics, logging |

### Frontend (apps/web)
| File | Changes |
|------|---------|
| `app/login/page.tsx` | NEW - Login page |
| `app/workflows/page.tsx` | NEW - Workflow list |
| `app/workflows/[id]/page.tsx` | NEW - Workflow detail |
| `app/dashboard/page.tsx` | NEW - Admin dashboard |
| `components/approval-card.tsx` | NEW - Approval UI |
| `components/audit-timeline.tsx` | NEW - Audit trail |
| `lib/api-client.ts` | NEW - API communication |
| `lib/hooks.ts` | NEW - React hooks |
| `app/layout.tsx` | Update for auth wrapper |

### Infrastructure
| File | Changes |
|------|---------|
| `docker-compose.yml` | Update services, add Redis, add worker |
| `.github/workflows/ci.yml` | Add integration tests |
| `.github/workflows/cd-containers.yml` | Add worker image build |
| `k8s/deployment.yaml` | NEW - K8s manifests |
| `docs/architecture.md` | NEW - Detailed docs |

---

## Effort Estimate

| Phase | Tasks | Developer Weeks | Notes |
|-------|-------|-----------------|-------|
| 1 | DB, Auth, Cache | 2 | Foundation work, highest priority |
| 2 | LangGraph, LLM, RAG | 1.5 | Requires LLM API key, cost implications |
| 3 | Connectors | 1 | API integrations, straightforward |
| 4 | Web UI | 1.5 | Iterative, can prioritize MVP UI first |
| 5 | Observability, Tests | 2 | Parallel with other phases |
| **Total** | | **8 weeks** | Assuming 1 FTE, can parallelize some tasks |

---

## Next Steps

1. **Immediately** (Today):
   - Review and approve this build plan
   - Assign owners to each phase
   - Set up project board with tasks

2. **This Week** (Phase 1 Kickoff):
   - Add dependencies to `pyproject.toml`
   - Stub out abstract repository interfaces
   - Create SQLAlchemy models
   - Write first Alembic migration

3. **Next Week** (Phase 1 Continued):
   - Complete PostgreSQL repository implementations
   - Set up JWT auth middleware
   - Implement Redis queue
   - Update bootstrap to use real storage

4. **Week 3** (Phase 2 Kickoff):
   - Design LangGraph workflow
   - Add LLM extraction with fallback
   - Write comprehensive tests

---

**Build Plan Version**: 1.0  
**Last Updated**: May 12, 2026  
**Status**: Ready for implementation
