import { ModuleCard } from "@/components/module-card";
import { platformModules, workflowSteps } from "@/lib/modules";

const stats = [
  { label: "System Layers", value: "6" },
  { label: "Primary APIs", value: "4" },
  { label: "Core Slice", value: "Workflow + Approval" },
];

export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow">Operational Intelligence Infrastructure</div>
        <h1>AI Orchestration for Real Enterprise Work.</h1>
        <p>
          This workspace is structured as a production-oriented platform: a FastAPI gateway,
          persistent operational core, stateful orchestration runtime, AI decision layer, and
          connector architecture for the systems companies already depend on.
        </p>
        <div className="hero-grid">
          {stats.map((stat) => (
            <div className="stat" key={stat.label}>
              <span className="stat-label">{stat.label}</span>
              <span className="stat-value">{stat.value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>Platform Modules</h2>
            <p>The repo is scaffolded around clear runtime boundaries so each layer can harden independently.</p>
          </div>
        </div>
        <div className="module-grid">
          {platformModules.map((module) => (
            <ModuleCard
              key={module.title}
              title={module.title}
              summary={module.summary}
              tags={module.tags}
            />
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-header">
          <div>
            <h2>First Implemented Flow</h2>
            <p>The initial vertical slice covers procurement-style intake through approvals and audit events.</p>
          </div>
        </div>
        <div className="workflow-strip">
          {workflowSteps.map((step) => (
            <div className="workflow-step" key={step.id}>
              <span>{step.id}</span>
              <strong>{step.label}</strong>
            </div>
          ))}
        </div>
        <div className="footer-note">
          Current implementation uses a local workflow runtime and in-memory repositories so we can grow the
          product shape quickly before swapping in PostgreSQL persistence, Redis queues, LangGraph state
          storage, and real provider credentials.
        </div>
      </section>
    </main>
  );
}
