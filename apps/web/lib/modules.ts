export const platformModules = [
  {
    title: "Frontend UI",
    summary:
      "Next.js operations console for workflow monitoring, approvals, operator views, and tenant-aware administration.",
    tags: ["Next.js", "Approval UX", "Dashboard"],
  },
  {
    title: "FastAPI Gateway",
    summary:
      "Public and internal APIs for workflow creation, approval handling, event publishing, tenancy, and role enforcement.",
    tags: ["FastAPI", "RBAC", "APIs"],
  },
  {
    title: "Operational Core",
    summary:
      "Persistent business entities, audit trails, repository adapters, queues, and the future PostgreSQL and Redis runtime.",
    tags: ["PostgreSQL", "Redis", "Audit"],
  },
  {
    title: "LangGraph Runtime",
    summary:
      "Stateful workflow coordination layer with retries, branching, approvals, and deterministic progression across nodes.",
    tags: ["State Graph", "Retries", "Humans"],
  },
  {
    title: "AI Layer",
    summary:
      "Extraction, policy reasoning, RAG, memory, and structured model calls that turn unstructured requests into actions.",
    tags: ["LLMs", "RAG", "Policy"],
  },
  {
    title: "Integration Layer",
    summary:
      "Reusable connector contracts for Slack, Gmail, Jira, Salesforce, ERP systems, and secure idempotent execution.",
    tags: ["Connectors", "Idempotency", "Retries"],
  },
];

export const workflowSteps = [
  { id: "01", label: "Trigger Intake" },
  { id: "02", label: "Extract Context" },
  { id: "03", label: "Evaluate Policy" },
  { id: "04", label: "Route Approval" },
  { id: "05", label: "Execute Action" },
  { id: "06", label: "Notify + Audit" },
];

