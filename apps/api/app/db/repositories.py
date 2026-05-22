from __future__ import annotations

from abc import ABC, abstractmethod
from threading import RLock

from fastapi import HTTPException, status

from app.domain.models import AuditLogRecord, WorkflowState


class BaseWorkflowRepository(ABC):
    """Abstract interface for workflow persistence."""

    @abstractmethod
    def create(self, workflow: WorkflowState) -> WorkflowState:
        """Create and store a new workflow."""
        raise NotImplementedError

    @abstractmethod
    def update(self, workflow: WorkflowState) -> WorkflowState:
        """Update an existing workflow."""
        raise NotImplementedError

    @abstractmethod
    def get(self, workflow_id: str) -> WorkflowState:
        """Retrieve a workflow by ID."""
        raise NotImplementedError

    @abstractmethod
    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[WorkflowState]:
        """List workflows for a tenant with pagination."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all workflows (for testing)."""
        raise NotImplementedError


class BaseAuditRepository(ABC):
    """Abstract interface for audit log persistence."""

    @abstractmethod
    def append(self, record: AuditLogRecord) -> AuditLogRecord:
        """Append an audit log record."""
        raise NotImplementedError

    @abstractmethod
    def list_by_workflow(self, workflow_id: str) -> list[AuditLogRecord]:
        """List all audit records for a workflow."""
        raise NotImplementedError

    @abstractmethod
    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[AuditLogRecord]:
        """List all audit records for a tenant with pagination."""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Clear all records (for testing)."""
        raise NotImplementedError


class InMemoryWorkflowRepository(BaseWorkflowRepository):
    """In-memory workflow repository for development/testing."""

    def __init__(self) -> None:
        self._items: dict[str, WorkflowState] = {}
        self._lock = RLock()

    def create(self, workflow: WorkflowState) -> WorkflowState:
        with self._lock:
            self._items[workflow.workflow_id] = workflow
            return workflow

    def update(self, workflow: WorkflowState) -> WorkflowState:
        with self._lock:
            self._items[workflow.workflow_id] = workflow
            return workflow

    def get(self, workflow_id: str) -> WorkflowState:
        workflow = self._items.get(workflow_id)
        if workflow is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' was not found.",
            )
        return workflow

    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[WorkflowState]:
        workflows = [w for w in self._items.values() if w.tenant_id == tenant_id]
        return workflows[skip : skip + limit]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class InMemoryAuditRepository(BaseAuditRepository):
    """In-memory audit repository for development/testing."""

    def __init__(self) -> None:
        self._items: list[AuditLogRecord] = []
        self._lock = RLock()

    def append(self, record: AuditLogRecord) -> AuditLogRecord:
        with self._lock:
            self._items.append(record)
            return record

    def list_by_workflow(self, workflow_id: str) -> list[AuditLogRecord]:
        return [record for record in self._items if record.workflow_id == workflow_id]

    def list_by_tenant(self, tenant_id: str, skip: int = 0, limit: int = 100) -> list[AuditLogRecord]:
        records = [record for record in self._items if record.tenant_id == tenant_id]
        return records[skip : skip + limit]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


class BaseUserRepository(ABC):
    @abstractmethod
    def create_user(self, user: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_id: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def list_users(self, tenant_id: str | None = None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: str, updates: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        raise NotImplementedError


class InMemoryUserRepository(BaseUserRepository):
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._lock = RLock()

    def create_user(self, user: dict) -> dict:
        with self._lock:
            self._items[user["user_id"]] = user
            return user

    def get_user(self, user_id: str) -> dict | None:
        return self._items.get(user_id)

    def list_users(self, tenant_id: str | None = None) -> list[dict]:
        if tenant_id:
            return [u for u in self._items.values() if u.get("tenant_id") == tenant_id]
        return list(self._items.values())

    def update_user(self, user_id: str, updates: dict) -> dict:
        with self._lock:
            user = self._items.get(user_id)
            if not user:
                raise KeyError("user not found")
            user.update(updates)
            self._items[user_id] = user
            return user

    def delete_user(self, user_id: str) -> None:
        with self._lock:
            if user_id in self._items:
                del self._items[user_id]


class BaseTenantRepository(ABC):
    @abstractmethod
    def create_tenant(self, tenant: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_tenants(self) -> list[dict]:
        raise NotImplementedError


class InMemoryTenantRepository(BaseTenantRepository):
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}
        self._lock = RLock()

    def create_tenant(self, tenant: dict) -> dict:
        with self._lock:
            self._items[tenant["tenant_id"]] = tenant
            return tenant

    def list_tenants(self) -> list[dict]:
        return list(self._items.values())


# Legacy aliases for backwards compatibility
WorkflowRepository = InMemoryWorkflowRepository
AuditRepository = InMemoryAuditRepository
