from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.bootstrap import get_container
from app.core.security import Principal, get_current_principal
from app.db.postgres import PostgresUserRepository
from app.observability.telemetry import MetricsCollector
from app.services.documents import DocumentIngestionService


def get_workflow_service():
    return get_container().workflow_service


def get_approval_service():
    return get_container().approval_service


def get_audit_service():
    return get_container().audit_service


def get_metrics_collector() -> MetricsCollector:
    return get_container().metrics_collector


def get_document_service() -> DocumentIngestionService:
    service = getattr(get_container(), "document_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document ingestion store is unavailable (PostgreSQL required).",
        )
    return service


def get_user_repository() -> PostgresUserRepository:
    repo = get_container().user_repository
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication store is unavailable (PostgreSQL required).",
        )
    return repo


def require_roles(*allowed_roles: str) -> Callable[[Principal], Principal]:
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_any_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The authenticated principal does not have access to this resource.",
            )
        return principal

    return dependency
