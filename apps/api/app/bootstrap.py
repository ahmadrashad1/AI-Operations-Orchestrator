import os

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from app.ai.llm_extraction import LLMExtractionAgent
from app.ai.policy import PolicyEngine
from app.ai.retrieval_pgvector import PGVectorRetrieval
from app.core.config import get_settings
from app.db.migrations import run_migrations
from app.db.postgres import PostgresAuditRepository, PostgresWorkflowRepository
from app.db.repositories import InMemoryAuditRepository, InMemoryWorkflowRepository
from app.db.repositories import InMemoryUserRepository
from app.db.repositories import InMemoryTenantRepository
from app.integrations.registry import ConnectorRegistry
from app.integrations.slack import SlackApprovalConnector
from app.orchestration.runtime import WorkflowRuntime
from app.observability.telemetry import MetricsCollector
from app.services.documents import DocumentIngestionService
from app.services.approvals import ApprovalService
from app.services.audit import AuditService
from app.services.reporting import ReportingService
from app.services.queue import RedisJobQueue
from app.services.workflows import WorkflowService
from app.services.users import UserService
from app.services.tenants import TenantService


class ServiceContainer:
    def __init__(self, use_postgres: bool | None = None) -> None:
        settings = get_settings()

        # Auto-detect based on environment if not specified
        if use_postgres is None:
            use_postgres = settings.environment != "development"

        # Initialize storage
        if use_postgres:
            self._init_postgres(settings)
        else:
            self._init_in_memory(settings)

        # Initialize job queue (always Redis, falls back to mock if unavailable)
        try:
            self.job_queue = RedisJobQueue(redis_url=settings.redis_url)
            if not self.job_queue.health_check():
                print("Warning: Redis unavailable, using mock job queue")
                self.job_queue = None
        except Exception as e:
            print(f"Warning: Failed to initialize Redis: {e}")
            self.job_queue = None

        # Initialize services
        self.metrics_collector = MetricsCollector()
        audit_service = AuditService(repository=self.audit_repository)
        connector_registry = ConnectorRegistry(
            connectors=[SlackApprovalConnector(webhook_url=settings.slack_webhook_url)]
        )
        runtime = WorkflowRuntime(
            extractor=LLMExtractionAgent(settings=settings, redis_url=settings.redis_url),
            policy_engine=PolicyEngine(settings=settings),
            audit_service=audit_service,
            connector_registry=connector_registry,
            job_queue=self.job_queue,
        )

        self.document_service = None
        if use_postgres:
            try:
                self.document_service = DocumentIngestionService(
                    retriever=PGVectorRetrieval(db_url=settings.database_url),
                    queue=self.job_queue,
                )
            except Exception as exc:
                print(f"Warning: Failed to initialize document ingestion service: {exc}")

        self.workflow_service = WorkflowService(
            repository=self.workflow_repository,
            audit_service=audit_service,
            runtime=runtime,
        )
        self.approval_service = ApprovalService(
            repository=self.workflow_repository,
            audit_service=audit_service,
            runtime=runtime,
        )
        self.audit_service = audit_service
        self.reporting_service = ReportingService(
            workflow_repository=self.workflow_repository,
            audit_repository=self.audit_repository,
        )
        # Ensure tenant service exists (in-memory for dev)
        if not getattr(self, "tenant_repository", None):
            self.tenant_repository = InMemoryTenantRepository()
            self.tenant_service = TenantService(self.tenant_repository)

    def _init_postgres(self, settings) -> None:
        """Initialize PostgreSQL storage."""
        # Create engine with connection pooling
        engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

        # Run migrations
        try:
            run_migrations(engine)
        except Exception as e:
            print(f"Warning: Failed to run migrations: {e}")

        self.engine = engine
        self.workflow_repository = PostgresWorkflowRepository(engine)
        self.audit_repository = PostgresAuditRepository(engine)
        # Postgres-backed user repository if available
        try:
            from app.db.postgres import PostgresUserRepository

            self.user_repository = PostgresUserRepository(engine)
        except Exception:
            self.user_repository = None

    def _init_in_memory(self, settings) -> None:
        """Initialize in-memory storage (for development/testing)."""
        self.engine = None
        self.workflow_repository = InMemoryWorkflowRepository()
        self.audit_repository = InMemoryAuditRepository()
        # lightweight in-memory user repository for dev/test
        self.user_repository = InMemoryUserRepository()
        self.user_service = UserService(self.user_repository)

    def reset_state(self) -> None:
        """Clear all state (for testing)."""
        self.workflow_repository.clear()
        self.audit_repository.clear()
        self.metrics_collector.clear()
        if self.job_queue:
            self.job_queue.clear_queue()

    def shutdown(self) -> None:
        """Clean up resources."""
        if self.engine:
            self.engine.dispose()


# Global container
_container: ServiceContainer | None = None


def init_container(use_postgres: bool | None = None) -> ServiceContainer:
    """Initialize the global service container."""
    global _container
    _container = ServiceContainer(use_postgres=use_postgres)
    return _container


def get_container() -> ServiceContainer:
    """Get the global service container."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container
