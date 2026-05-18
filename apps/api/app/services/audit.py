from app.db.repositories import AuditRepository
from app.domain.models import AuditLogRecord


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def log(
        self,
        workflow_id: str,
        actor: str,
        action: str,
        metadata: dict | None = None,
        tenant_id: str = "",
    ) -> AuditLogRecord:
        record = AuditLogRecord(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            actor=actor,
            action=action,
            metadata=metadata or {},
        )
        return self.repository.append(record)

    def list_for_workflow(self, workflow_id: str) -> list[AuditLogRecord]:
        return self.repository.list_by_workflow(workflow_id=workflow_id)

